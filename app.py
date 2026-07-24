from flask import Flask, render_template, request, redirect, url_for #kütüphaneyi kullanmak ve gerekli araçları çağırmak için 
import os #operating system, bilgisayarın işletim sistemiyle iletişimi sağlar

import psycopg2 #siteye yüklenen verilerin kalıcı olması için kullanılacak mini veritabanı kütüphanesi
from psycopg2.extras import RealDictCursor

import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__) #web sitesinin motorunu çalıştıran ana komut
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)


# VERİTABANI FONKSİYONLARI
def veritabani_baglan():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
     )

def veritabani_kur():
    # İlk çalıştırmada tabloları otomatik oluşturur
    baglanti = veritabani_baglan()
    cursor = baglanti.cursor() #veritabanı içinde işlem yapmamızı sağlayan dijital bir kalem oluşturur
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gonderiler (
            id SERIAL PRIMARY KEY, 
            yazar TEXT NOT NULL,
            puan INTEGER NOT NULL DEFAULT 5,
            dosya_yollari TEXT NOT NULL,
            public_idler TEXT NOT NULL
        )
    ''')
    baglanti.commit()
    cursor.close()
    baglanti.close()

# Uygulama başlarken veritabanını hazırla
veritabani_kur()

@app.route('/')
def anasayfa():
    admin_kontrol = request.args.get('admin') == '1'
    baglanti = veritabani_baglan()
    cursor = baglanti.cursor()
    # Tüm gönderileri veritabanından çekiyoruz
    cursor.execute('SELECT * FROM gonderiler ORDER BY id DESC')
    db_gonderiler = cursor.fetchall()
    cursor.close()
    baglanti.close()
    
    # Veritabanından gelen veriyi HTML'in anlayacağı listeye çeviriyoruz
    islenmis_galeri = []
    for gonderi in db_gonderiler:
        gonderi_puani= gonderi['puan'] if 'puan' in gonderi.keys() else 5

        islenmis_galeri.append({
            "id": gonderi['id'],
            "yazar": gonderi['yazar'],
            "puan": gonderi_puani,
            # Veritabanına metin olarak kaydettiğimiz yolları tekrar listeye çeviriyoruz
            "dosya_yollari": gonderi['dosya_yollari'].split(',')
        })
        
    return render_template('index.html', galeri=islenmis_galeri, admin_mi=admin_kontrol)

@app.route('/sil/<int:gonderi_id>')
def gonderi_sil(gonderi_id):
    # GÜVENLİK KONTROLÜ: Şifre adreste doğru belirtilmemişse işlemi reddet
    if request.args.get('sifre') != 'sevvalcan2026':
        return "Bu işlem için yetkiniz yok!", 403
        
    baglanti = veritabani_baglan()
    cursor = baglanti.cursor()
    
    # Bilgisayarın klasöründeki resim dosyalarını da fiziksel olarak silmek için önce yolları çekiyoruz
    cursor.execute("SELECT dosya_yollari, public_idler FROM gonderiler WHERE id = %s", (gonderi_id,))
    gonderi = cursor.fetchone()
    
    if gonderi:
        # Veritabanındaki virgülle ayrılmış yolları listeye çevirip tek tek dosyaları siliyoruz
        public_idler = gonderi['public_idler'].split(',')
        for public_id in public_idler:
          cloudinary.uploader.destroy(public_id)  
                
        # Dosyalar klasörden silindikten sonra veritabanı satırını da temizliyoruz
        cursor.execute("DELETE FROM gonderiler WHERE id = %s",(gonderi_id,))
        baglanti.commit()

    cursor.close()    
    baglanti.close()
    
    # Silme bittikten sonra yine admin modu açık kalacak şekilde anasayfaya yönlendir
    return redirect(url_for('anasayfa', admin='1'))

@app.route('/yukle', methods=['GET', 'POST'])
def fotograf_yukle():
    if request.method == 'POST':
        yazar = request.form.get('yazar')
        gelen_dosyalar = request.files.getlist('fotograflar')
        
        if len(gelen_dosyalar) > 5:
            return "en fazla 5 fotoğraf yükleyebilirsiniz!", 400
            
        kaydedilen_yollar = []
        kaydedilen_public_idler = []
        for dosya in gelen_dosyalar:
            if dosya.filename != '':
                 sonuc = cloudinary.uploader.upload(dosya)
                 kaydedilen_yollar.append(sonuc["secure_url"])
                 kaydedilen_public_idler.append(sonuc["public_id"]) 

        if kaydedilen_yollar:
            # Fotoğraf yollarını aralarına virgül koyarak tek bir metin haline getiriyoruz
            yollar_metni = ",".join(kaydedilen_yollar)
            public_idler_metni = ",".join(kaydedilen_public_idler)
            
            # VERİTABANINA KAYDETME
            baglanti = veritabani_baglan()
            cursor = baglanti.cursor()
            cursor.execute("INSERT INTO gonderiler (yazar, dosya_yollari, public_idler) VALUES (%s, %s, %s)",(yazar, yollar_metni, public_idler_metni))
            baglanti.commit()
            cursor.close()
            baglanti.close()
            
        return redirect(url_for('anasayfa'))
        
    return render_template('yaz.html')

if __name__ == '__main__':
    app.run (
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
      )