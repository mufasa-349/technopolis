#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Technopolis ürün URL'lerinden görselleri çeken ve Excel'e link olarak yazan script
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse, urlunparse
import json
import re

# Ayarlar
EXCEL_FILE = 'Technopolis_Tum_Urunler_20250917_164841_Brands_Translated_NoDuplicates (1).xlsx'
DELAY = 1  # Her istek arasında bekleme süresi (saniye)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def convert_to_full_size_image(img_url):
    """Thumbnail veya küçük görsel URL'ini orijinal büyük görsele çevirir"""
    if not img_url:
        return img_url
    
    # 71x71, 100x100 gibi küçük boyutları orijinal boyuta çevir
    # Önce yaygın pattern'leri kontrol et
    
    # Pattern 1: /71x71/, /100x100/ gibi küçük boyutları büyük boyutla değiştir
    size_pattern = r'/(\d+)x(\d+)/'
    match = re.search(size_pattern, img_url)
    if match:
        width, height = int(match.group(1)), int(match.group(2))
        # Eğer küçük bir boyutsa (örneğin 71x71, 100x100), boyut kısmını kaldır
        # (orijinal görsel URL'sini elde etmek için)
        if width <= 200 or height <= 200:
            # Boyut kısmını tamamen kaldır (orijinal boyut için)
            img_url = re.sub(size_pattern, '/', img_url)
    
    # Pattern 2: thumb, thumbnail, small gibi kelimeler
    img_url = re.sub(r'/thumb(?:nail)?s?/', '/large/', img_url, flags=re.IGNORECASE)
    img_url = re.sub(r'/small/', '/large/', img_url, flags=re.IGNORECASE)
    img_url = re.sub(r'thumb(?:nail)?', 'large', img_url, flags=re.IGNORECASE)
    img_url = re.sub(r'_small', '_large', img_url, flags=re.IGNORECASE)
    img_url = re.sub(r'_thumb', '_large', img_url, flags=re.IGNORECASE)
    
    # Pattern 3: Query parametrelerinde boyut varsa kaldır veya değiştir
    parsed = urlparse(img_url)
    if parsed.query:
        # width, height, size gibi parametreleri kaldır
        query_params = []
        for param in parsed.query.split('&'):
            if not any(key in param.lower() for key in ['width', 'height', 'size', 'w=', 'h=']):
                query_params.append(param)
        new_query = '&'.join(query_params)
        img_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    
    # Pattern 4: URL'de _71x71_ gibi pattern varsa
    img_url = re.sub(r'_\d+x\d+_', '_', img_url)
    
    # Pattern 5: URL sonunda ?w=71&h=71 gibi parametreler
    img_url = re.sub(r'[?&](?:w|width|h|height|size)=\d+', '', img_url)
    img_url = img_url.rstrip('&?')
    
    return img_url

def get_images_from_url(url):
    """Verilen URL'den ürün görsellerini çeker"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        images = []
        
        # Farklı görsel kaynaklarını dene
        
        # 0. ÖNCE: Modal/Gallery için data attribute'larını kontrol et (büyük görseller için)
        # data-zoom-url, data-large-url, data-full-url, data-original gibi attribute'ları ara
        for img in soup.find_all(['img', 'a', 'div'], attrs=lambda x: x and any(key in x for key in ['data-zoom-url', 'data-large-url', 'data-full-url', 'data-original', 'data-zoom', 'data-lightbox', 'data-gallery-url', 'data-href'])):
            for attr in ['data-zoom-url', 'data-large-url', 'data-full-url', 'data-original', 'data-zoom', 'data-lightbox', 'data-gallery-url', 'data-href']:
                large_url = img.get(attr)
                if large_url:
                    images.append(large_url)
        
        # 0.1: Gallery modal için özel attribute'lar
        gallery_items = soup.find_all(attrs={'data-image': True}) + soup.find_all(attrs={'data-thumb': True})
        for item in gallery_items:
            if item.get('data-image'):
                images.append(item.get('data-image'))
            if item.get('data-thumb'):
                # data-thumb genelde küçük görseldir, ama bazen data-image ile birlikte gelir
                pass
        
        # 1. img etiketlerini kontrol et (product images için)
        product_images = soup.find_all('img', class_=lambda x: x and ('product' in x.lower() or 'gallery' in x.lower() or 'main' in x.lower()))
        
        # 2. picture source etiketlerini kontrol et
        picture_tags = soup.find_all('picture')
        for picture in picture_tags:
            source_tags = picture.find_all('source')
            img_tags = picture.find_all('img')
            for source in source_tags:
                if source.get('srcset'):
                    # srcset'teki tüm görselleri al, en büyük olanı seç
                    srcset_items = source.get('srcset').split(',')
                    # En büyük görseli bul (genişlik değerine göre)
                    largest_url = None
                    largest_size = 0
                    for item in srcset_items:
                        parts = item.strip().split()
                        url_part = parts[0]
                        # Boyut bilgisini al (varsa)
                        size = 0
                        if len(parts) > 1:
                            try:
                                size = int(re.sub(r'[^0-9]', '', parts[1]))
                            except:
                                pass
                        if size > largest_size:
                            largest_size = size
                            largest_url = url_part
                    if largest_url:
                        images.append(largest_url)
                    else:
                        # Boyut bilgisi yoksa, tüm URL'leri ekle
                        images.extend([src.split()[0] for src in srcset_items])
            for img in img_tags:
                # img etiketlerinde srcset varsa, en büyük olanı seç
                if img.get('srcset'):
                    srcset_items = img.get('srcset').split(',')
                    largest_url = None
                    largest_size = 0
                    for item in srcset_items:
                        parts = item.strip().split()
                        url_part = parts[0]
                        size = 0
                        if len(parts) > 1:
                            try:
                                size = int(re.sub(r'[^0-9]', '', parts[1]))
                            except:
                                pass
                        if size > largest_size:
                            largest_size = size
                            largest_url = url_part
                    if largest_url:
                        images.append(largest_url)
                if img.get('src'):
                    images.append(img.get('src'))
                if img.get('data-src'):
                    images.append(img.get('data-src'))
        
        # 3. data-src veya lazy-loaded görseller
        lazy_images = soup.find_all('img', {'data-src': True})
        for img in lazy_images:
            images.append(img.get('data-src'))
        
        # 4. Genel img etiketleri (yüksek çözünürlüklü olanları)
        all_images = soup.find_all('img')
        for img in all_images:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src and any(keyword in src.lower() for keyword in ['product', 'gallery', 'main', 'zoom', 'big', 'large']):
                if src not in images:
                    images.append(src)
        
        # 5. JavaScript'te embed edilmiş görseller (API çağrıları vb)
        # 5.1: application/json type script'ler - Technopolis özel yapısı
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Technopolis özel yapısı: cx-state.product.details.entities.{productId}.variants.value.images.GALLERY
                    if 'cx-state' in data and 'product' in data['cx-state']:
                        product_state = data['cx-state'].get('product', {})
                        if 'details' in product_state and 'entities' in product_state['details']:
                            for product_id, product_data in product_state['details']['entities'].items():
                                try:
                                    if 'variants' in product_data and 'value' in product_data['variants']:
                                        variants = product_data['variants']['value']
                                        if 'images' in variants:
                                            # PRIMARY görseli (ana görsel)
                                            if 'PRIMARY' in variants['images']:
                                                primary = variants['images']['PRIMARY']
                                                if isinstance(primary, dict) and 'videoluxZoom' in primary:
                                                    zoom_url = primary['videoluxZoom'].get('url')
                                                    if zoom_url:
                                                        images.append(zoom_url)
                                            
                                            # GALLERY görselleri (diğer görseller) - videoluxZoom formatını öncelikli al
                                            if 'GALLERY' in variants['images']:
                                                gallery = variants['images']['GALLERY']
                                                if isinstance(gallery, list):
                                                    for gallery_item in gallery:
                                                        if isinstance(gallery_item, dict):
                                                            # Önce videoluxZoom'u dene (en büyük boyut)
                                                            if 'videoluxZoom' in gallery_item:
                                                                zoom_url = gallery_item['videoluxZoom'].get('url')
                                                                if zoom_url:
                                                                    images.append(zoom_url)
                                                            # Fallback: videoluxProduct
                                                            elif 'videoluxProduct' in gallery_item:
                                                                prod_url = gallery_item['videoluxProduct'].get('url')
                                                                if prod_url:
                                                                    images.append(prod_url)
                                except:
                                    pass
                    
                    # Genel nested structure kontrolü (fallback)
                    def extract_urls(obj, urls_list):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if 'image' in key.lower() or 'photo' in key.lower() or 'img' in key.lower() or 'media' in key.lower() or 'gallery' in key.lower():
                                    if isinstance(value, str) and (value.startswith('http') or value.startswith('//')):
                                        urls_list.append(value)
                                    elif isinstance(value, list):
                                        for item in value:
                                            if isinstance(item, str) and (item.startswith('http') or item.startswith('//')):
                                                urls_list.append(item)
                                extract_urls(value, urls_list)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_urls(item, urls_list)
                    
                    # Eğer Technopolis yapısında görsel bulunamadıysa, genel arama yap
                    if not any('technopolis.bg' in img for img in images):
                        extract_urls(data, images)
            except:
                pass
        
        # 5.2: Tüm script tag'lerinde product images array'lerini ara
        all_scripts = soup.find_all('script')
        for script in all_scripts:
            if not script.string:
                continue
            script_text = script.string
            
            # JavaScript object'lerinde product images array'lerini ara
            # Pattern: images: [...], productImages: [...], gallery: [...], media: [...]
            patterns = [
                r'(?:images|productImages|gallery|media|productMedia)\s*[:=]\s*\[(.*?)\]',
                r'(?:zoom|large|full)Images\s*[:=]\s*\[(.*?)\]',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, script_text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    array_content = match.group(1)
                    # URL'leri çıkar
                    url_matches = re.findall(r'["\'](https?://[^"\']+)["\']', array_content)
                    images.extend(url_matches)
                    # Göreceli URL'ler için
                    rel_urls = re.findall(r'["\'](/[^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', array_content, re.IGNORECASE)
                    images.extend(rel_urls)
            
            # JSON.parse() içindeki verileri ara
            json_matches = re.finditer(r'JSON\.parse\(["\'](.*?)["\']\)', script_text, re.DOTALL)
            for json_match in json_matches:
                try:
                    json_str = json_match.group(1).replace('\\"', '"').replace("\\'", "'")
                    json_data = json.loads(json_str)
                    def extract_from_obj(obj):
                        if isinstance(obj, dict):
                            for key, val in obj.items():
                                if any(kw in key.lower() for kw in ['image', 'gallery', 'media', 'zoom', 'large']):
                                    if isinstance(val, str) and ('http' in val or val.startswith('/')):
                                        images.append(val)
                                    elif isinstance(val, list):
                                        for item in val:
                                            if isinstance(item, str) and ('http' in item or item.startswith('/')):
                                                images.append(item)
                                extract_from_obj(val)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_from_obj(item)
                    extract_from_obj(json_data)
                except:
                    pass
        
        # URL'leri normalize et
        normalized_images = []
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        for img_url in images:
            if not img_url:
                continue
            # Göreceli URL'leri mutlak URL'lere çevir
            if img_url.startswith('//'):
                img_url = f"{urlparse(url).scheme}:{img_url}"
            elif img_url.startswith('/'):
                img_url = urljoin(base_url, img_url)
            elif not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            
            # Tekrarları temizle ve geçerli görselleri filtrele
            if img_url not in normalized_images and any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                normalized_images.append(img_url)
        
        # Logo, icon gibi görselleri filtrele ve küçük görselleri büyük versiyonlarına çevir
        filtered_images = []
        exclude_keywords = ['logo', 'icon', 'banner', 'placeholder', 'blank', 'no-image', 'social']
        
        for img_url in normalized_images:
            if not any(keyword in img_url.lower() for keyword in exclude_keywords):
                # videoluxZoom ve videoluxProduct URL'leri zaten büyük görseller, dönüştürme yapma
                is_videolux_url = 'videoluxzoom' in img_url.lower() or 'videoluxproduct' in img_url.lower() or 'product-zoom' in img_url.lower()
                
                if is_videolux_url:
                    # Zaten büyük görsel, direkt ekle
                    full_size_url = img_url
                else:
                    # Küçük görselleri (thumbnail'ler) orijinal büyük versiyonlarına çevir
                    full_size_url = convert_to_full_size_image(img_url)
                
                # videoluxZoom URL'lerini en öncelikli yap (büyük görseller)
                if 'videoluxzoom' in img_url.lower() or 'product-zoom' in img_url.lower():
                    filtered_images.insert(0, full_size_url)
                # Ürün görseli gibi görünen URL'leri önceliklendir
                elif any(keyword in img_url.lower() for keyword in ['product', 'gallery', 'main', 'zoom', 'big', 'large', '/p/', '/products/']):
                    filtered_images.insert(0, full_size_url)
                else:
                    filtered_images.append(full_size_url)
        
        # Tekrarları temizle (aynı görselin farklı boyutları olabilir)
        unique_images = []
        seen = set()
        for img_url in filtered_images:
            # URL'yi normalize et (protocol, domain olmadan karşılaştır)
            normalized = urlparse(img_url).path.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_images.append(img_url)
        
        # En fazla 10 görsel döndür
        return unique_images[:10]
        
    except Exception as e:
        print(f"  Hata: {str(e)}")
        return []

def main():
    print("Excel dosyası okunuyor...")
    df = pd.read_excel(EXCEL_FILE)
    
    # Product URL sütununu kontrol et
    url_column = 'Product URL'
    if url_column not in df.columns:
        print(f"Hata: '{url_column}' sütunu bulunamadı!")
        print(f"Mevcut sütunlar: {df.columns.tolist()}")
        return
    
    # Yeni sütunları ekle (eğer yoksa)
    if 'Ana görsel' not in df.columns:
        df['Ana görsel'] = ''
    if 'Diğer görseller' not in df.columns:
        df['Diğer görseller'] = ''
    
    # Boş olmayan URL'leri filtrele
    df_with_urls = df[df[url_column].notna()].copy()
    total_products = len(df_with_urls)
    
    print(f"Toplam {total_products} ürün bulundu.")
    print(f"Görsel linkleri Excel'e yazılacak.\n")
    
    # İlerleme için stats
    stats = {
        'success': 0,
        'no_images': 0
    }
    
    # Her kaç üründe bir Excel'i kaydet (ilerlemeyi korumak için)
    SAVE_INTERVAL = 10
    
    for idx, (index, row) in enumerate(df_with_urls.iterrows(), 1):
        product_id = row.get('Product ID', f'product_{index}')
        product_name = row.get('Product Name', 'Unknown')
        url = row[url_column]
        
        print(f"[{idx}/{total_products}] Product ID: {product_id}")
        print(f"  Ürün: {product_name[:50]}...")
        print(f"  URL: {url}")
        
        # Görselleri çek
        images = get_images_from_url(url)
        
        if not images:
            print(f"  ⚠️  Görsel bulunamadı!")
            stats['no_images'] += 1
            # Excel'de boş bırak (zaten boş)
        else:
            print(f"  ✅ {len(images)} görsel bulundu")
            
            # İlk görseli "Ana görsel" sütununa yaz
            if len(images) > 0:
                df.at[index, 'Ana görsel'] = images[0]
                print(f"    ✓ Ana görsel: {images[0][:80]}...")
            
            # Diğer görselleri "Diğer görseller" sütununa virgülle ayırarak yaz
            if len(images) > 1:
                other_images = images[1:]
                df.at[index, 'Diğer görseller'] = ', '.join(other_images)
                print(f"    ✓ {len(other_images)} diğer görsel eklendi")
            
            stats['success'] += 1
        
        # Her SAVE_INTERVAL üründe bir veya son ürün ise Excel'i kaydet
        if idx % SAVE_INTERVAL == 0 or idx == total_products:
            print(f"\n💾 İlerleme kaydediliyor... ({idx}/{total_products})")
            df.to_excel(EXCEL_FILE, index=False)
            print(f"✅ Excel dosyası güncellendi: {EXCEL_FILE}\n")
        
        # Rate limiting için bekle
        time.sleep(DELAY)
        print()
    
    # Son bir kez daha kaydet (güvence için)
    print("\nExcel dosyası güncelleniyor...")
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Excel dosyası güncellendi: {EXCEL_FILE}")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    print(f"Başarılı: {stats['success']}")
    print(f"Görsel bulunamayan: {stats['no_images']}")
    print(f"Toplam: {total_products}")

if __name__ == '__main__':
    main()

