#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechnoMarket.bg sitesinden ürün bilgilerini çeken script
Bulgarca metinleri Türkçe'ye çevirir
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse
import json
import re

# Çeviri için (deep-translator kullanılacak)
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("⚠️  deep-translator paketi bulunamadı. Çeviri yapılmayacak.")
    print("   Yüklemek için: pip install deep-translator")

# Ayarlar
BASE_URL = 'https://www.technomarket.bg'
EXCEL_FILE = 'TechnoMarket_Urunler.xlsx'
DELAY = 2  # Her istek arasında bekleme süresi (saniye)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def translate_text(text, source='bg', target='tr'):
    """Bulgarca metni Türkçe'ye çevirir"""
    if not TRANSLATOR_AVAILABLE or not text or pd.isna(text):
        return text
    
    try:
        text_str = str(text).strip()
        if not text_str:
            return text
        
        translator = GoogleTranslator(source=source, target=target)
        translated = translator.translate(text_str)
        time.sleep(0.5)  # Rate limiting
        return translated
    except Exception as e:
        print(f"    Çeviri hatası: {str(e)}")
        return text

def extract_price(price_text):
    """Fiyat metninden sayısal değeri çıkarır (tam sayı olarak)"""
    if not price_text:
        return None
    
    # Sayıları ve noktayı bul
    price_str = re.sub(r'[^\d.,]', '', str(price_text))
    price_str = price_str.replace(',', '.').replace(' ', '')
    
    try:
        # Virgülden sonraki kısmı at, tam sayı döndür
        price_float = float(price_str)
        return int(price_float)
    except:
        return None

def get_product_details(product_url, timeout=3):
    """Ürün sayfasından detayları çeker"""
    try:
        response = requests.get(product_url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        product_data = {
            'product_id': None,
            'product_name': None,
            'price': None,
            'category': None,
            'brand': None,
            'description': None,
            'images': [],
            'ean': None
        }
        
        # Ürün adı - önce .name span'ından al
        name_elem = soup.select_one('.name')
        if name_elem:
            product_data['product_name'] = name_elem.get_text(strip=True)
        else:
            # Alternatif seçiciler
            name_selectors = [
                'h1.product-title',
                'h1.product-name',
                '.product-title',
                'h1',
                '[class*="product"][class*="name"]',
                '[class*="product"][class*="title"]'
            ]
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    product_data['product_name'] = name_elem.get_text(strip=True)
                    break
        
        # Fiyat - TechnoMarket özel yapısı
        # <div class="price"><tm-price> içinde <span class="bgn"><span class="primary">1,099</span><span class="secondary">00</span></span>
        price_elem = soup.select_one('.price tm-price .bgn')
        if price_elem:
            # primary ve secondary span'larını bul
            primary = price_elem.select_one('.primary')
            secondary = price_elem.select_one('.secondary')
            
            if primary:
                primary_text = primary.get_text(strip=True)
                secondary_text = secondary.get_text(strip=True) if secondary else '00'
                
                # Binlik ayıracı (virgül) ve boşlukları temizle
                primary_text = primary_text.replace(',', '').replace(' ', '').strip()
                secondary_text = secondary_text.replace(',', '').replace(' ', '').strip()
                
                # Fiyatı birleştir (1099.00 gibi)
                price_text = f"{primary_text}.{secondary_text}"
                product_data['price'] = extract_price(price_text)
        
        # Eğer yukarıdaki yapı çalışmadıysa, genel yöntemi dene
        if not product_data['price']:
            price_selectors = [
                '.price',
                '.product-price',
                '[class*="price"]',
                '[data-price]'
            ]
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    product_data['price'] = extract_price(price_text)
                    if product_data['price']:
                        break
        
        # EAN/Barkod - tm-pointandplace elementinin ean attribute'ünden al
        pointandplace = soup.select_one('tm-pointandplace')
        if pointandplace:
            ean = pointandplace.get('ean')
            if ean:
                product_data['ean'] = ean.strip()
        
        # Eğer tm-pointandplace'den bulunamadıysa, alternatif yöntemleri dene
        if not product_data['ean']:
            ean_patterns = [
                r'EAN[:\s]*(\d+)',
                r'Barkod[:\s]*(\d+)',
                r'Код на продукта[:\s]*(\d+)'
            ]
            for pattern in ean_patterns:
                match = re.search(pattern, soup.get_text(), re.IGNORECASE)
                if match:
                    product_data['ean'] = match.group(1)
                    break
        
        # Ürün ID - Şu an EAN olarak bulunan değeri kullan (Код на продукта)
        # Eğer bulunamazsa URL'den al
        product_code_patterns = [
            r'Код на продукта[:\s]*(\d+)',
            r'Код[:\s]*(\d+)',
        ]
        for pattern in product_code_patterns:
            match = re.search(pattern, soup.get_text(), re.IGNORECASE)
            if match:
                product_data['product_id'] = match.group(1)
                break
        
        # Eğer hala bulunamadıysa URL'den al
        if not product_data['product_id']:
            url_match = re.search(r'/p/(\d+)|/product/(\d+)|product-(\d+)|/(\d{8})$', product_url)
            if url_match:
                product_data['product_id'] = url_match.group(1) or url_match.group(2) or url_match.group(3) or url_match.group(4)
        
        # Marka - önce data-brand attribute'ünden al (çeviri yok)
        brand_elem = soup.select_one('[data-brand]')
        if brand_elem:
            product_data['brand'] = brand_elem.get('data-brand', '').strip()
        
        # Eğer data-brand bulunamadıysa, diğer yöntemleri dene
        if not product_data['brand']:
            brand_selectors = [
                '[class*="brand"]',
                '.product-brand'
            ]
            for selector in brand_selectors:
                brand_elem = soup.select_one(selector)
                if brand_elem:
                    product_data['brand'] = brand_elem.get_text(strip=True)
                    break
        
        # Kategori
        category_selectors = [
            '.breadcrumb a',
            '[class*="breadcrumb"] a',
            '[class*="category"]'
        ]
        for selector in category_selectors:
            cat_elems = soup.select(selector)
            if cat_elems:
                product_data['category'] = cat_elems[-1].get_text(strip=True)
                break
        
        # Açıklama - .collapsed-content .product-basic ul li elementlerinden
        desc_items = []
        
        # Önce .collapsed-content .product-basic ul li'den çek
        basic_info = soup.select('.collapsed-content .product-basic ul li')
        if basic_info:
            for li in basic_info:
                text = li.get_text(strip=True)
                if text:
                    # İkon metnini temizle (✓ işaretini kaldır)
                    text = re.sub(r'^[^\w]*', '', text)
                    if text:
                        desc_items.append(text)
        
        # Eğer bulunamadıysa alternatif yöntemleri dene
        if not desc_items:
            desc_selectors = [
                '.product-description',
                '[class*="description"]',
                '.product-details'
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if desc_text:
                        desc_items.append(desc_text)
                        break
        
        # Açıklamaları birleştir (satır başı ile)
        if desc_items:
            product_data['description'] = '\n'.join(desc_items)
        else:
            product_data['description'] = ''
        
        # Görseller - .slider-content içinden çek
        slider_content = soup.select_one('.slider-content')
        if slider_content:
            imgs = slider_content.find_all('img')
            for img in imgs:
                # Önce src, sonra data-src'yi kontrol et
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    # URL'yi normalize et
                    if img_url.startswith('//'):
                        img_url = f"https:{img_url}"
                    elif img_url.startswith('/'):
                        img_url = urljoin(BASE_URL, img_url)
                    
                    # Tekrarları önle
                    if img_url and img_url not in product_data['images']:
                        product_data['images'].append(img_url)
        
        # Eğer slider-content'ten görsel bulunamadıysa, alternatif yöntemleri dene
        if not product_data['images']:
            img_selectors = [
                '.product-gallery img',
                '.product-images img',
                '[class*="product"] img[src]',
                'img[data-zoom-url]',
                'img[data-large-url]'
            ]
            for selector in img_selectors:
                imgs = soup.select(selector)
                for img in imgs:
                    img_url = img.get('src') or img.get('data-src') or img.get('data-zoom-url') or img.get('data-large-url')
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = f"https:{img_url}"
                        elif img_url.startswith('/'):
                            img_url = urljoin(BASE_URL, img_url)
                        if img_url not in product_data['images']:
                            product_data['images'].append(img_url)
                if product_data['images']:
                    break
        
        return product_data
    
    except Exception as e:
        print(f"  Hata: {str(e)}")
        return None

def get_category_products(category_url, max_products=100):
    """Kategori sayfasından ürün URL'lerini çıkarır"""
    try:
        products = []
        page = 1
        
        while len(products) < max_products:
            # Sayfa numarasını URL'ye ekle
            if '?' in category_url:
                page_url = f"{category_url}&page={page}"
            else:
                page_url = f"{category_url}?page={page}"
            
            response = requests.get(page_url, headers=HEADERS, timeout=10)
            
            if response.status_code != 200:
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ürün linklerini bul
            product_links = soup.find_all('a', href=re.compile(r'/p/|/product/'))
            
            found_new = False
            for link in product_links:
                href = link.get('href', '')
                if href:
                    if href.startswith('/'):
                        full_url = urljoin(BASE_URL, href)
                    elif not href.startswith('http'):
                        continue
                    else:
                        full_url = href
                    
                    if full_url not in products:
                        products.append(full_url)
                        found_new = True
                        if len(products) >= max_products:
                            break
            
            if not found_new:
                break
            
            page += 1
            time.sleep(DELAY)
        
        return products[:max_products]
    
    except Exception as e:
        print(f"Hata: {str(e)}")
        return []

def create_excel_template():
    """Excel şablonunu oluşturur"""
    columns = [
        'Product ID',
        'Barkod (EAN Number)',
        'Product Name',
        'Price',
        'Currency',
        'Category',
        'Brand',
        'Ana görsel',
        'Image 1',
        'Image 2',
        'Image 3',
        'Image 4',
        'Image 5',
        'Diğer görseller',
        'Product URL'
    ]
    
    df = pd.DataFrame(columns=columns)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Excel şablonu oluşturuldu: {EXCEL_FILE}")

def main():
    print("TechnoMarket.bg Ürün Çekme Scripti")
    print("="*60)
    
    # Excel dosyasını oluştur
    create_excel_template()
    
    # Kullanıcıdan kategori seçimi
    print("\nKategori URL'lerini girin (her satıra bir URL, boş satır ile bitirin):")
    category_urls = []
    while True:
        url = input().strip()
        if not url:
            break
        if url:
            if not url.startswith('http'):
                url = urljoin(BASE_URL, url)
            category_urls.append(url)
    
    if not category_urls:
        print("⚠️  Kategori URL'i girilmedi!")
        return
    
    print(f"\n✅ {len(category_urls)} kategori işlenecek")
    
    # Excel dosyasını oku
    df = pd.read_excel(EXCEL_FILE)
    
    # İstatistikler
    total_products = 0
    stats = {'success': 0, 'failed': 0}
    
    # Her kategori için ürünleri çek
    for cat_idx, category_url in enumerate(category_urls, 1):
        print(f"\n[{cat_idx}/{len(category_urls)}] Kategori işleniyor: {category_url}")
        
        # Ürün URL'lerini al
        product_urls = get_category_products(category_url)
        print(f"  ✅ {len(product_urls)} ürün bulundu")
        
        # Her ürün için detayları çek
        for prod_idx, product_url in enumerate(product_urls, 1):
            print(f"  [{prod_idx}/{len(product_urls)}] Ürün işleniyor...")
            print(f"    URL: {product_url}")
            
            # Ürün detaylarını çek
            product_data = get_product_details(product_url)
            
            if not product_data:
                print(f"    ✗ Ürün bilgileri çekilemedi")
                stats['failed'] += 1
                time.sleep(DELAY)
                continue
            
            # Yeni satır oluştur
            new_row = {
                'Product ID': product_data.get('product_id', ''),
                'Barkod (EAN Number)': product_data.get('ean', ''),
                'Product Name': translate_text(product_data.get('product_name', '')),
                'Price': product_data.get('price'),
                'Currency': 'BGN',
                'Category': translate_text(product_data.get('category', '')),
                'Brand': translate_text(product_data.get('brand', '')),
                'Product URL': product_url,
                'Ana görsel': product_data['images'][0] if product_data['images'] else '',
                'Image 1': product_data['images'][1] if len(product_data['images']) > 1 else '',
                'Image 2': product_data['images'][2] if len(product_data['images']) > 2 else '',
                'Image 3': product_data['images'][3] if len(product_data['images']) > 3 else '',
                'Image 4': product_data['images'][4] if len(product_data['images']) > 4 else '',
                'Image 5': product_data['images'][5] if len(product_data['images']) > 5 else '',
                'Diğer görseller': ', '.join(product_data['images'][6:]) if len(product_data['images']) > 6 else ''
            }
            
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            total_products += 1
            stats['success'] += 1
            
            print(f"    ✓ Ürün eklendi: {new_row['Product Name'][:50]}...")
            
            # Her 10 üründe bir kaydet
            if total_products % 10 == 0:
                print(f"\n💾 İlerleme kaydediliyor... ({total_products} ürün)")
                df.to_excel(EXCEL_FILE, index=False)
            
            time.sleep(DELAY)
    
    # Son kayıt
    print("\n💾 Excel dosyası güncelleniyor...")
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Excel dosyası güncellendi: {EXCEL_FILE}")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    print(f"Başarılı: {stats['success']}")
    print(f"Başarısız: {stats['failed']}")
    print(f"Toplam: {total_products}")

if __name__ == '__main__':
    main()

