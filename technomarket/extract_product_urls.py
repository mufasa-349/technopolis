#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechnoMarket.bg grid sayfasından ürün linklerini çeken script
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

BASE_URL = 'https://www.technomarket.bg'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
EXCEL_FILE = 'Product_URLs.xlsx'
DELAY = 1  # Her istek arasında bekleme süresi

def extract_product_urls(page_url):
    """Sayfadan ürün linklerini çıkarır - tm-product-item yapısından"""
    try:
        print(f"Sayfa çekiliyor: {page_url}")
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        product_urls = []
        seen = set()
        
        # tm-product-item elementlerini bul
        product_items = soup.find_all('tm-product-item')
        
        if not product_items:
            # Alternatif: direkt product-image veya title class'lı linkleri bul
            product_items = soup.find_all('a', class_=['product-image', 'title'])
        
        for item in product_items:
            # Eğer tm-product-item ise, içindeki linkleri bul
            if item.name == 'tm-product-item':
                links = item.find_all('a', href=True)
            else:
                links = [item] if item.get('href') else []
            
            for link in links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # URL'yi normalize et
                if href.startswith('/'):
                    full_url = urljoin(BASE_URL, href)
                elif href.startswith('http') and 'technomarket.bg' in href:
                    full_url = href
                else:
                    continue
                
                # Ürün sayfası linklerini filtrele (kategori değil)
                # Örnek: /televizor/neo-led-32h3m-hd-led-tv-09218598
                if '/produkti/' not in full_url and full_url not in seen:
                    seen.add(full_url)
                    product_urls.append(full_url)
        
        # Tekrarları temizle ve sırala
        unique_urls = list(dict.fromkeys(product_urls))  # Sırayı koruyarak tekrarları kaldır
        
        print(f"  ✅ {len(unique_urls)} ürün linki bulundu")
        return unique_urls
    
    except Exception as e:
        print(f"  ✗ Hata: {str(e)}")
        return []

def main():
    print("TechnoMarket.bg Ürün Link Çekici")
    print("="*60)
    
    # Kullanıcıdan URL al
    print("\nGrid sayfasının URL'sini girin:")
    print("(Örnek: https://www.technomarket.bg/produkti/televizor)")
    page_url = input().strip()
    
    if not page_url:
        print("⚠️  URL girilmedi!")
        return
    
    if not page_url.startswith('http'):
        page_url = urljoin(BASE_URL, page_url)
    
    print(f"\nİşlenen URL: {page_url}")
    print("-" * 60)
    
    # Ürün linklerini çek
    all_urls = []
    
    # İlk sayfadan ürünleri çek
    urls = extract_product_urls(page_url)
    all_urls.extend(urls)
    
    # Sayfalama varsa diğer sayfaları da çek
    print("\nSayfalama kontrol ediliyor...")
    page_num = 2
    max_pages = 100  # Maksimum sayfa sayısı
    
    while page_num <= max_pages:
        # Sayfa URL'sini oluştur (technomarket.bg formatına göre)
        # URL formatı: /produkti/televizor?page=2
        if '?' in page_url:
            # Zaten parametre var, page ekle veya güncelle
            if 'page=' in page_url:
                next_page_url = re.sub(r'page=\d+', f'page={page_num}', page_url)
            else:
                next_page_url = f"{page_url}&page={page_num}"
        else:
            next_page_url = f"{page_url}?page={page_num}"
        
        time.sleep(DELAY)
        urls = extract_product_urls(next_page_url)
        
        if not urls:
            print(f"  Sayfa {page_num}'de ürün bulunamadı, sayfalama sona erdi.")
            break
        
        # Önceki sayfalarda olan URL'ler varsa durdur
        new_urls = [u for u in urls if u not in all_urls]
        if not new_urls:
            print(f"  Sayfa {page_num}'de yeni ürün yok, sayfalama sona erdi.")
            break
        
        all_urls.extend(new_urls)
        print(f"  Toplam {len(all_urls)} ürün linki toplandı")
        
        page_num += 1
    
    # Tekrarları temizle
    final_urls = list(dict.fromkeys(all_urls))
    
    print(f"\n✅ Toplam {len(final_urls)} benzersiz ürün linki bulundu")
    
    # Excel'e kaydet
    print("\n💾 Excel dosyasına kaydediliyor...")
    df = pd.DataFrame({
        'Product URL': final_urls
    })
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Ürün linkleri '{EXCEL_FILE}' dosyasına kaydedildi")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    print(f"Toplam ürün sayısı: {len(final_urls)}")
    print(f"Excel dosyası: {EXCEL_FILE}")
    
    # İlk 5 linki göster
    if final_urls:
        print("\nİlk 5 ürün linki:")
        for i, url in enumerate(final_urls[:5], 1):
            print(f"  {i}. {url}")

if __name__ == '__main__':
    main()

