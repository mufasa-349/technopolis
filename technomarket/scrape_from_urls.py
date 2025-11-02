#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product_URLs.xlsx dosyasındaki linklerden ürün bilgilerini çeken script
"""

import pandas as pd
import sys
import os

# scrape_technomarket.py'deki fonksiyonları import et
from scrape_technomarket import (
    get_product_details,
    translate_text,
    BASE_URL,
    DELAY,
    HEADERS
)
import time

# Ayarlar
PRODUCT_URLS_FILE = 'Product_URLs.xlsx'
OUTPUT_FILE = 'TechnoMarket_Urunler.xlsx'
MAX_PRODUCTS = 5  # İlk kaç ürün işlenecek

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
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Excel şablonu oluşturuldu: {OUTPUT_FILE}")

def main():
    print("TechnoMarket.bg Ürün Detay Çekici")
    print("="*60)
    
    # Product_URLs.xlsx dosyasını kontrol et
    if not os.path.exists(PRODUCT_URLS_FILE):
        print(f"❌ Hata: '{PRODUCT_URLS_FILE}' dosyası bulunamadı!")
        return
    
    print(f"\n📂 '{PRODUCT_URLS_FILE}' dosyası okunuyor...")
    try:
        urls_df = pd.read_excel(PRODUCT_URLS_FILE)
        
        if 'Product URL' not in urls_df.columns:
            print(f"❌ Hata: 'Product URL' sütunu bulunamadı!")
            print(f"Mevcut sütunlar: {urls_df.columns.tolist()}")
            return
        
        product_urls = urls_df['Product URL'].dropna().astype(str).tolist()
        product_urls = [url.strip() for url in product_urls if url.strip()]
        
        print(f"✅ {len(product_urls)} ürün linki bulundu")
        
        # İlk MAX_PRODUCTS kadarını al
        if len(product_urls) > MAX_PRODUCTS:
            product_urls = product_urls[:MAX_PRODUCTS]
            print(f"⚠️  İlk {MAX_PRODUCTS} ürün işlenecek")
        
        print(f"📝 Toplam {len(product_urls)} ürün işlenecek")
        
    except Exception as e:
        print(f"❌ Dosya okuma hatası: {str(e)}")
        return
    
    # Excel şablonunu oluştur veya mevcut dosyayı oku
    try:
        if os.path.exists(OUTPUT_FILE):
            print(f"\n📂 Mevcut Excel dosyası bulundu: {OUTPUT_FILE}")
            df = pd.read_excel(OUTPUT_FILE)
            print(f"  ✅ {len(df)} mevcut ürün yüklendi")
        else:
            create_excel_template()
            df = pd.read_excel(OUTPUT_FILE)
    except Exception as e:
        print(f"⚠️  Excel dosyası okunamadı, yeni oluşturuluyor: {str(e)}")
        create_excel_template()
        df = pd.read_excel(OUTPUT_FILE)
    
    # İstatistikler
    stats = {'success': 0, 'failed': 0}
    
    # Her ürün için detayları çek
    print("\n" + "="*60)
    print("Ürün detayları çekiliyor...")
    print("="*60)
    
    for idx, product_url in enumerate(product_urls, 1):
        print(f"\n[{idx}/{len(product_urls)}] Ürün işleniyor...")
        print(f"  URL: {product_url}")
        
        # Ürün detaylarını çek (3 saniye timeout)
        try:
            product_data = get_product_details(product_url, timeout=3)
        except Exception as e:
            print(f"  ✗ Timeout veya hata: {str(e)}")
            stats['failed'] += 1
            time.sleep(DELAY)
            continue
        
        if not product_data:
            print(f"  ✗ Ürün bilgileri çekilemedi")
            stats['failed'] += 1
            time.sleep(DELAY)
            continue
        
        # Fiyat kontrolü - 100 BGN altı ürünleri atla
        price = product_data.get('price')
        if price is None or price < 100:
            if price is None:
                print(f"  ⚠️  Fiyat bulunamadı, atlanıyor")
            else:
                print(f"  ⚠️  Fiyat {price} BGN (< 100 BGN), atlanıyor")
            stats['failed'] += 1
            time.sleep(DELAY)
            continue
        
        # Ürün adını işle: Marka + çevrilmiş ürün adı
        brand = product_data.get('brand', '').strip()
        product_name = product_data.get('product_name', '').strip()
        
        # Ürün adını çevir
        translated_name = translate_text(product_name) if product_name else ''
        
        # Markayı başa ekle
        if brand and translated_name:
            final_product_name = f"{brand} {translated_name}"
        elif brand:
            final_product_name = brand
        elif translated_name:
            final_product_name = translated_name
        else:
            final_product_name = ''
        
        # Görselleri dağıt: İlk görsel Ana görsel, sonraki 5 görsel Image 1-5
        images = product_data.get('images', [])
        
        # Yeni satır oluştur
        new_row = {
            'Product ID': product_data.get('product_id', ''),
            'Barkod (EAN Number)': product_data.get('ean', ''),
            'Product Name': final_product_name,
            'Price': product_data.get('price'),
            'Currency': 'BGN',
            'Category': translate_text(product_data.get('category', '')),
            'Brand': brand,  # Marka çevrilmez, olduğu gibi alınır
            'Product URL': product_url,
            'Ana görsel': images[0] if len(images) > 0 else '',
            'Image 1': images[1] if len(images) > 1 else '',
            'Image 2': images[2] if len(images) > 2 else '',
            'Image 3': images[3] if len(images) > 3 else '',
            'Image 4': images[4] if len(images) > 4 else '',
            'Image 5': images[5] if len(images) > 5 else '',
            'Diğer görseller': ''  # Boş bırakılıyor
        }
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        stats['success'] += 1
        
        print(f"  ✓ Ürün eklendi: {new_row['Product Name'][:50] if new_row['Product Name'] else 'N/A'}...")
        print(f"    Fiyat: {new_row['Price']} BGN" if new_row['Price'] else "    Fiyat: Bulunamadı")
        print(f"    Görseller: {len(product_data['images'])} adet")
        
        # Her üründe bir kaydet (güvenlik için)
        df.to_excel(OUTPUT_FILE, index=False)
        
        time.sleep(DELAY)
    
    # Son kayıt
    print("\n💾 Excel dosyası güncelleniyor...")
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Excel dosyası güncellendi: {OUTPUT_FILE}")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    print(f"Başarılı: {stats['success']}")
    print(f"Başarısız: {stats['failed']}")
    print(f"Toplam işlenen: {len(product_urls)}")
    print(f"Toplam ürün sayısı (Excel'de): {len(df)}")

if __name__ == '__main__':
    main()

