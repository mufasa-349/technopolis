#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechnoMarket.bg sitesindeki kategorileri listeleyen script
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = 'https://www.technomarket.bg'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_categories():
    """Ana sayfadan kategorileri çıkarır"""
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        categories = []
        
        # Menü yapısını bul
        # Kategori linklerini ara
        category_links = soup.find_all('a', href=True)
        
        seen = set()
        for link in category_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Kategori URL'lerini filtrele
            if href and text:
                # URL'yi normalize et
                if href.startswith('/'):
                    full_url = urljoin(BASE_URL, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                
                # Aynı URL'yi tekrar ekleme
                if full_url in seen:
                    continue
                
                # Kategori gibi görünen linkleri al
                if any(keyword in full_url.lower() for keyword in ['/category/', '/c/', '/products/', '/shop/']):
                    seen.add(full_url)
                    categories.append({
                        'name': text,
                        'url': full_url
                    })
                # Ana menü linklerini de kontrol et
                elif '/bg/' in full_url and len(text) > 3 and len(text) < 100:
                    # Ana sayfa, giriş gibi linkleri atla
                    exclude = ['home', 'login', 'register', 'cart', 'profile', 'search', 'contact']
                    if not any(ex in full_url.lower() for ex in exclude):
                        seen.add(full_url)
                        categories.append({
                            'name': text,
                            'url': full_url
                        })
        
        return categories
    
    except Exception as e:
        print(f"Hata: {str(e)}")
        return []

def main():
    print("TechnoMarket.bg kategorileri çekiliyor...")
    print("="*60)
    
    categories = get_categories()
    
    if not categories:
        print("⚠️  Kategori bulunamadı. Sayfa yapısını kontrol edin.")
        return
    
    print(f"\n✅ Toplam {len(categories)} kategori bulundu:\n")
    
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat['name']}")
        print(f"   URL: {cat['url']}")
        print()
    
    # Kategorileri dosyaya kaydet
    with open('technomarket_categories.txt', 'w', encoding='utf-8') as f:
        f.write("TechnoMarket.bg Kategorileri\n")
        f.write("="*60 + "\n\n")
        for i, cat in enumerate(categories, 1):
            f.write(f"{i}. {cat['name']}\n")
            f.write(f"   URL: {cat['url']}\n\n")
    
    print(f"✅ Kategoriler 'technomarket_categories.txt' dosyasına kaydedildi.")

if __name__ == '__main__':
    main()

