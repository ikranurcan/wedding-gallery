from flask import Flask, render_template, request, redirect, url_for #kütüphaneyi kullanmak ve gerekli araçları çağırmak için 
import os #operating system, bilgisayarın işletim sistemiyle iletişimi sağlar
import sqlite3 #siteye yüklenen verilerin kalıcı olması için kullanılacak mini veritabanı kütüphanesi

app = Flask(__name__) #web sitesinin motorunu çalıştıran ana komut

UPLOAD_FOLDER = os.path.join('static', 'uploads') #yüklenen fotoğrafların bilgisayarda hangi klasöre kaydedileceğini belirler
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) #bilgisayara eğer static/upload adında klasör yoksa hemen oluştur varsa da hata verme aynen devam et der

# VERİTABANI FONKSİYONLARI
def veritabani_baglan():
    # SQLITE veritabanı dosyasına bağlanır
    baglanti = sqlite3.connect('veritabani.db')
    baglanti.row_factory = sqlite3.Row # Verileri sözlük yapısında alabilmek için
    return baglanti

def veritabani_kur():
    # İlk çalıştırmada tabloları otomatik oluşturur
    baglanti = veritabani_baglan()
    cursor = baglanti.cursor() #veritabanı içinde işlem yapmamızı sağlayan dijital bir kalem oluşturur
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gonderiler (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            yazar TEXT NOT NULL,
            dosya_yollari TEXT NOT NULL
        )
    ''')
    baglanti.commit()
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
    cursor.execute('SELECT dosya_yollari FROM gonderiler WHERE id = ?', (gonderi_id,))
    gonderi = cursor.fetchone()
    
    if gonderi:
        # Veritabanındaki virgülle ayrılmış yolları listeye çevirip tek tek dosyaları siliyoruz
        yollar = gonderi['dosya_yollari'].split(',')
        for yol in yollar:
            # Başındaki eğik çizgiyi temizleyerek 'static/uploads/...' formatına getirir
            temiz_yol = yol.lstrip('/') 
            if os.path.exists(temiz_yol):
                os.remove(temiz_yol)
                
        # Dosyalar klasörden silindikten sonra veritabanı satırını da temizliyoruz
        cursor.execute('DELETE FROM gonderiler WHERE id = ?', (gonderi_id,))
        baglanti.commit()
        
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
        for dosya in gelen_dosyalar:
            if dosya.filename != '':
                dosya_yolu = os.path.join(app.config['UPLOAD_FOLDER'], dosya.filename)
                dosya.save(dosya_yolu)
                web_yolu = f"/static/uploads/{dosya.filename}"
                kaydedilen_yollar.append(web_yolu)
                
        if kaydedilen_yollar:
            # Fotoğraf yollarını aralarına virgül koyarak tek bir metin haline getiriyoruz
            yollar_metni = ",".join(kaydedilen_yollar)
            
            # VERİTABANINA KAYDETME
            baglanti = veritabani_baglan()
            cursor = baglanti.cursor()
            cursor.execute('INSERT INTO gonderiler (yazar, dosya_yollari) VALUES (?, ?)', (yazar, yollar_metni))
            baglanti.commit()
            baglanti.close()
            
        return redirect(url_for('anasayfa'))
        
    return render_template('yaz.html')

if __name__ == '__main__':
    app.run(
        host="0.0.0.0"
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )