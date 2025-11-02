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
import os

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
                
                # PDF linklerini at
                if '.pdf' in full_url.lower():
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
    
    # Mevcut Excel dosyasını oku (varsa)
    existing_urls = []
    try:
        if os.path.exists(EXCEL_FILE):
            print(f"\n📂 Mevcut Excel dosyası bulundu: {EXCEL_FILE}")
            existing_df = pd.read_excel(EXCEL_FILE)
            if 'Product URL' in existing_df.columns:
                existing_urls = existing_df['Product URL'].dropna().astype(str).tolist()
                existing_urls = [url.strip() for url in existing_urls if url.strip()]
                print(f"  ✅ {len(existing_urls)} mevcut ürün linki yüklendi")
            else:
                print("  ⚠️  'Product URL' sütunu bulunamadı, yeni dosya oluşturulacak")
    except Exception as e:
        print(f"  ⚠️  Mevcut dosya okunamadı: {str(e)}")
        print("  Yeni dosya oluşturulacak")
    
    # Kullanıcıdan toplu URL listesi al
    print("\nGrid sayfalarının URL'lerini girin (her satıra bir URL, boş satır ile bitirin):")
    print("(Örnek: https://www.technomarket.bg/produkti/televizor)")
    
    page_urls = []
    while True:
        url = input().strip()
        if not url:
            break
        if url:
            if not url.startswith('http'):
                url = urljoin(BASE_URL, url)
            page_urls.append(url)
    
    if not page_urls:
        print("⚠️  URL girilmedi!")
        return
    
    print(f"\n✅ {len(page_urls)} kategori URL'si alındı")
    print("-" * 60)
    
    # Ürün linklerini çek (mevcut URL'leri de dahil et)
    all_urls = list(existing_urls)  # Mevcut URL'leri başlangıç listesine ekle
    
    # Her kategori URL'si için işlem yap
    for cat_idx, page_url in enumerate(page_urls, 1):
        print(f"\n[{cat_idx}/{len(page_urls)}] İşlenen kategori: {page_url}")
        print("-" * 60)
        
        # İlk sayfadan ürünleri çek
        urls = extract_product_urls(page_url)
        all_urls.extend(urls)
        
        # Sayfalama varsa diğer sayfaları da çek
        print("Sayfalama kontrol ediliyor...")
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
        
        print(f"✅ Kategori {cat_idx} tamamlandı. Toplam {len(all_urls)} ürün linki")
        time.sleep(DELAY)  # Kategoriler arası bekleme
    
    # Tekrarları temizle
    final_urls = list(dict.fromkeys(all_urls))
    
    # Yeni eklenen URL sayısını hesapla
    new_urls_count = len(final_urls) - len(existing_urls)
    
    print(f"\n✅ Toplam {len(final_urls)} benzersiz ürün linki bulundu")
    if existing_urls:
        print(f"   ({len(existing_urls)} mevcut + {new_urls_count} yeni)")
    
    # Excel'e kaydet
    print("\n💾 Excel dosyasına kaydediliyor...")
    df = pd.DataFrame({
        'Product URL': final_urls
    })
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Ürün linkleri '{EXCEL_FILE}' dosyasına kaydedildi")
    if new_urls_count > 0:
        print(f"   (+{new_urls_count} yeni link eklendi)")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    print(f"İşlenen kategori sayısı: {len(page_urls)}")
    print(f"Toplam ürün sayısı: {len(final_urls)}")
    if existing_urls:
        print(f"  - Mevcut: {len(existing_urls)}")
        print(f"  - Yeni eklenen: {new_urls_count}")
    print(f"Excel dosyası: {EXCEL_FILE}")
    
    # İlk 5 linki göster
    if final_urls:
        print("\nİlk 5 ürün linki:")
        for i, url in enumerate(final_urls[:5], 1):
            print(f"  {i}. {url}")

if __name__ == '__main__':
    main()

