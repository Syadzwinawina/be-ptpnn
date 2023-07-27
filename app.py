import base64
import json
import os
from flask import Flask, request, jsonify, make_response
import pymysql
import mysql.connector
from binary_search import binary_search
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import io

# from prettytable import PrettyTable

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='',
    database='sounding'
)

cursor = conn.cursor()

@app.route('/hello', methods=['GET'])
def welcome():
    return "Hello World!"

@app.route('/login', methods=['POST'])
def login():
    user_id = request.json['user_id']
    password = request.json['password']

    sql = "SELECT * FROM users WHERE user_id = %s AND password = %s"
    val = (user_id, password)
    cursor.execute(sql, val)
    account = cursor.fetchone()

    if account:
        response = {
            "data":account,
            "error": "false"
        } 
    else:
        response = {
            'message': 'user_id atau password yang anda masukkan salah!'
        }
    return jsonify(response)



def connect_to_database():
    # Koneksi ke database MySQL
    cnx = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='sounding'
    )
    return cnx


@app.route('/sounding', methods=['POST'])
def sounding():
    try:
        # Mengambil input dari body JSON
        nama = request.json['nama']
        tangki_input = request.json['tangki']
        tinggi_input = float(request.json['tinggi'])
        suhu_input = float(request.json['suhu'])
        beda_input = float(request.json['beda'])
        meja_input = float(request.json['meja'])

        # Koneksi ke database MySQL
        cnx = connect_to_database()
        cursor = cnx.cursor()

        # Menjalankan query untuk mengambil data tangki yang tersedia
        cursor.execute("SELECT DISTINCT keterangan FROM cpo")
        data_tangki = cursor.fetchall()

        # Mengubah hasil eksekusi menjadi list
        data_list_tangki = [tangki[0] for tangki in data_tangki]

        if tangki_input not in data_list_tangki:
            return jsonify({"error": "Tangki tidak ditemukan"})

        # Menjalankan query untuk mengambil data dari tabel cpo yang dipilih
        cursor.execute("""
            SELECT tinggi, volume, beda, keterangan
            FROM cpo
            WHERE keterangan = %s
        """, (tangki_input,))
        # mengambil semua data query CPO
        data_cpo = cursor.fetchall()
        
        # Menjalankan query untuk mengambil data dari tabel suhu yang dipilih
        cursor.execute("""
            SELECT s.temperatur, s.berat_jenis
            FROM suhu_cpo AS s
        """)
        # mengambil semua data query CPO
        data_suhu = cursor.fetchall()

        # Mengubah hasil eksekusi menjadi list
        data_list_cpo = [list(row) for row in data_cpo]
        data_list_suhu = [list(row) for row in data_suhu]

        # Mencari nilai tinggi menggunakan binary search
        hasil = binary_search(data_list_cpo, tinggi_input)
        hasil_suhu = binary_search(data_list_suhu, suhu_input)

        if hasil != -1:
            # Tinggi ditemukan di tangki yang dipilih
            # Lakukan operasi atau perhitungan yang sesuai
            cpo = data_list_cpo[hasil][1]
            print("Hasil volume:", cpo)
        else:
            return jsonify({"error": "Tinggi tidak ditemukan di tangki yang dipilih"})
             
        if hasil_suhu != -1:
            # Tinggi ditemukan di tangki yang dipilih
            # Lakukan operasi atau perhitungan yang sesuai
            suhu = data_list_suhu[hasil_suhu][1]
            print("Hasil suhu:", suhu)
        else:
            return jsonify({"error": "Suhu tidak ditemukan di tangki yang dipilih"})

        if hasil != -1:
            # Menghitung nilai beda
            beda = data_list_cpo[hasil][2] * beda_input

            if hasil_suhu != -1:
                # Membuat fungsi untuk menghitung hasil perkalian campur dengan jumlah
                def perkalian_campur_jumlah(a, b, c, d):
                    return (a + b + c) * d

                # Memanggil fungsi dengan inputan yang telah dimasukkan
                sounding = perkalian_campur_jumlah(meja_input, data_list_cpo[hasil][1], beda, data_list_suhu[hasil_suhu][1])

                # Menampilkan hasil perhitungan
                print("Hasil Sounding:", sounding)
            else:
                return jsonify({"error": "Tidak dapat menghitung hasil Sounding karena nilai suhu tidak ditemukan."})
        else:
            return jsonify({"error": "Tidak dapat menghitung hasil Sounding karena nilai tangki tidak ditemukan."})

        # Menyimpan riwayat input dan output
        tangki = tangki_input
        temperatur_suhu = suhu_input
        tinggi = tinggi_input
        volume = cpo
        beda = beda_input
        hasil_sounding = sounding

        # Menyimpan riwayat ke dalam database
        waktu = datetime.now()
        
        # Mengkonversi nilai hasil_sounding ke bentuk float sebelum diinsert ke database
        hasil_sounding_decimal = float(hasil_sounding)


        sql_insert_sounding = "INSERT INTO hasil_s (waktu, nama, tangki, temperatur_suhu, tinggi, volume, beda, hasil_sounding) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        val_insert_sounding = (waktu, nama, tangki, temperatur_suhu, tinggi, volume, beda, hasil_sounding_decimal)
        cursor.execute(sql_insert_sounding, val_insert_sounding)
        cnx.commit()
        print("Riwayat sounding berhasil disimpan.")

        # Menutup koneksi database
        cursor.close()
        cnx.close()

        return jsonify({"error":"false","message": "Data Sounding telah dihitung", "hasil" : hasil_sounding, "volume" :volume, "suhu" : temperatur_suhu})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})


@app.route('/sounding', methods=['GET'])
def sounding_form():
    try:
        # Koneksi ke database MySQL
        cnx = connect_to_database()
        cursor = cnx.cursor()

        # Menjalankan query untuk mengambil data tangki yang tersedia
        cursor.execute("SELECT DISTINCT keterangan FROM cpo")
        data_tangki = cursor.fetchall()

        # Mengubah hasil eksekusi menjadi list
        data_list_tangki = [tangki[0] for tangki in data_tangki]

        # Menutup koneksi database
        cursor.close()
        cnx.close()

        # return render_template('sounding_form.html', data_tangki=data_list_tangki)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    

@app.route('/rendemen', methods=['POST'])
def rendemen():
    try:
        # Mengambil data dari body JSON
        data = request.json

        nama = data['nama']
        pengiriman = float(data['pengiriman'])
        stok_awal = float(data['stok_awal'])
        jumlah_rebusan = int(data['jumlah_rebusan'])
        tanggal = data['tanggal']

        # Koneksi ke database MySQL
        cnx = connect_to_database()
        cursor = cnx.cursor()

        # Menghitung TBS olah
        TBS_olah = jumlah_rebusan * 10 * 2500
        print("Hasil TBS Olah:", TBS_olah)

        # Mengambil hasil rendemen pada tanggal yang sama
        sql_check_sounding = "SELECT hasil_rendemen FROM hasil_r WHERE DATE(waktu) = %s"
        val_check_sounding = (tanggal,)
        cursor.execute(sql_check_sounding, val_check_sounding)
        result_sounding = cursor.fetchone()

        if result_sounding and result_sounding[0] > 0:
            print("Rendemen telah dilakukan pada tanggal tersebut.")
            return jsonify({
                "error": "true",
                "message": "Rendemen telah dilakukan pada tanggal tersebut"
            })
        else:
            # Mengambil hasil sounding pada tanggal yang sama
            sql_get_recent_sounding = "SELECT hasil_sounding FROM hasil_s WHERE DATE(waktu) = %s"
            val_get_recent_sounding = (tanggal,)
            cursor.execute(sql_get_recent_sounding, val_get_recent_sounding)
            result_recent_sounding = cursor.fetchall()

            if result_recent_sounding:
                hasil_sounding = len(result_recent_sounding)
                print("hasil 1:", hasil_sounding)
                total_sounding = sum([row[0] for row in result_recent_sounding])
                print("hasil 2:", total_sounding)
                akurasi = total_sounding / hasil_sounding
                print("hasil 3:", akurasi)
                

                # Menghitung hasil rendemen
                hasil_cpo = akurasi - pengiriman - stok_awal
                print("Hasil CPO:", hasil_cpo)

                # Menghitung hasil Rendemen
                hasil_rendemen = (hasil_cpo * 100) / TBS_olah
                print("Hasil Rendemen:", hasil_rendemen)
                
                # Ubah hasil_cpo dan hasil_rendemen menjadi positif jika nilai negatif
                hasil_cpo = abs(hasil_cpo)
                hasil_rendemen = abs(hasil_rendemen)


                waktu = datetime.now()

                sql_insert_rendemen = "INSERT INTO hasil_r (waktu, nama, pengiriman, stok_awal, jumlah_rebusan, TBS_olah, hasil_cpo, hasil_rendemen) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                val_insert_rendemen = (waktu, nama, pengiriman, stok_awal, jumlah_rebusan, TBS_olah, hasil_cpo, hasil_rendemen)
                cursor.execute(sql_insert_rendemen, val_insert_rendemen)
                cnx.commit()
                print("Riwayat rendemen berhasil disimpan.")

                return jsonify({
                    "error": "false",
                    "message": "Data Rendemen telah dihitung",
                    "hasil_rendemen": abs(hasil_rendemen),
                    "hasil_cpo": abs(hasil_cpo),  # Mengubah hasil_cpo menjadi positif
                    "TBS_olah": TBS_olah
                })
            else:
                print("Tidak ada hasil sounding yang tersedia pada tanggal tersebut.")
                return jsonify({
                    "error": "true",
                    "message": "Tidak ada hasil sounding yang tersedia pada tanggal tersebut"
                })

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})

    
    
@app.route('/grafik_sounding', methods=['GET'])
def get_grafik_sounding():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sounding"
    )

    # Membuat kursor
    cursor = db.cursor()

    # Menjalankan query untuk mengambil data dari database
    query = "SELECT waktu, hasil_sounding FROM hasil_s"
    cursor.execute(query)

    # Mendapatkan hasil query
    results = cursor.fetchall()

    # Memisahkan data kolom X dan Y
    x_values = []
    y_values = []

    # Memisahkan tanggal dan bulan dari waktu
    for result in results:
        waktu = result[0]
        tanggal = datetime.strftime(waktu, "%d")
        x_values.append(tanggal)
        y_values.append(result[1])

    # Menutup kursor dan koneksi database
    cursor.close()
    db.close()

    # Membuat grafik menggunakan Matplotlib
    plt.plot(x_values, y_values)
    plt.xlabel('Tanggal')
    plt.ylabel('Sounding')
    plt.title('Grafik dari Database MySQL')
    plt.xticks(rotation=45)

    # Menyimpan grafik ke file
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    base64_data = base64.b64encode(buf.read()).decode('utf-8')

    # Menghasilkan respons JSON dengan data grafik
    response = {
        'x_values': x_values,
        'y_values': y_values,
        'base64_data': base64_data
    }

    # Menentukan header dan respons JSON
    resp = make_response(jsonify(response))
    resp.headers['Access-Control-Allow-Origin'] = '*'

    return resp




@app.route('/grafik_rendemen', methods=['GET'])
def get_grafik_rendemen():
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sounding"
        )

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data dari database
        query = "SELECT waktu, hasil_rendemen FROM hasil_r"
        cursor.execute(query)

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Memisahkan data kolom X dan Y
        x_values = []
        y_values = []

        # Memisahkan tanggal dan bulan dari waktu
        for result in results:
            waktu = result[0]
            tanggal = datetime.strftime(waktu, "%d")
            x_values.append(tanggal)
            y_values.append(result[1])

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        # Membuat grafik menggunakan Matplotlib
        plt.plot(x_values, y_values)
        plt.xlabel('Tanggal')
        plt.ylabel('Rendemen')
        plt.title('Grafik Rendemen dari Database MySQL')
        plt.xticks(rotation=45)  # Memutar label sumbu x agar tidak tumpang tindih

        # Menyimpan grafik ke file
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        base64_data = base64.b64encode(buf.read()).decode('utf-8')

        # Menghasilkan respons JSON dengan data grafik
        response = {
            'x_values': x_values,
            'y_values': y_values,
            'base64_data': base64_data
        }
        
        # Menentukan header dan respons JSON
        resp = make_response(jsonify(response))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        
        return resp



# Fungsi untuk menambahkan akun
def tambah_akun(user_id, id_akun, nama, nik, password, jabatan):
    try:
        cnx = connect_to_database()
        cursor = cnx.cursor()

        # Memasukkan data akun ke tabel "akun"
        cursor.execute("INSERT INTO akun (id) VALUES ('{}')".format(user_id))
        id_akun = cursor.lastrowid

        # Menambahkan data akun ke tabel "users"
        sql = "INSERT INTO users (user_id, id_akun, nama, nik, password, jabatan) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (user_id, id_akun, nama, nik, password, jabatan)
        cursor.execute(sql, val)

        # Commit perubahan dan tutup kursor serta koneksi
        cnx.commit()
        cursor.close()
        cnx.close()
        print("Pembuatan akun sukses!")

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        raise

@app.route('/tambah_akun', methods=['POST'])
def handle_tambah_akun():
    try:
        data = request.get_json()
        user_id = data['user_id']
        nama = data['nama']
        nik = data['nik']
        password = data['password']
        jabatan = data['jabatan']

        tambah_akun(user_id, None, nama, nik, password, jabatan)

        return jsonify({"message": "Data berhasil ditambahkan"})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
    
def tambah_cpo(id, tinggi, volume, beda, keterangan):
    try:
        cnx = connect_to_database()
        cursor = cnx.cursor()


        # Menambahkan data akun ke tabel "users"
        sql = "INSERT INTO cpo (id, tinggi, volume, beda, keterangan) VALUES (%s, %s, %s, %s, %s)"
        val = (id, tinggi, volume, beda, keterangan)
        cursor.execute(sql, val)

        # Commit perubahan dan tutup kursor serta koneksi
        cnx.commit()
        cursor.close()
        cnx.close()
        print("Penambahan tabel cpo sukses!")

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        raise

@app.route('/tambah_cpo', methods=['POST'])
def handle_tambah_cpo():
    try:
        data = request.get_json()
        id = data['id']
        tinggi = data['tinggi']
        volume = data['volume']
        beda = data['beda']
        keterangan = data['keterangan']

        tambah_cpo(id, tinggi, volume, beda, keterangan)

        return jsonify({"message": "Data berhasil ditambahkan"})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    


@app.route('/edit_pengguna', methods=['POST'])
def edit_pengguna():
    try:
        data = request.get_json()
        user_id = data['user_id']
        nama = data['nama']
        nik = data['nik']
        password = data['password']
        jabatan = data['jabatan']

        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk memeriksa apakah user ID pengguna ada dalam database
        query = "SELECT * FROM users WHERE user_id = %s"
        values = (user_id,)
        cursor.execute(query, values)
        user = cursor.fetchone()

        if user:
            # Menjalankan query untuk mengubah data pengguna
            query = "UPDATE users SET nama = %s, nik = %s, password = %s, jabatan = %s WHERE user_id = %s"
            values = (nama, nik, password, jabatan, user_id)
            cursor.execute(query, values)

            # Melakukan commit perubahan ke database
            db.commit()

            response = {
                "message": "Data pengguna berhasil diubah!"
            }
        else:
            response = {
                "error": "User ID tidak ditemukan!"
            }

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify(response)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})


@app.route('/edit_cpo', methods=['POST'])
def edit_cpo():
    try:
        data = request.get_json()
        id = data['id']
        tinggi = data['tinggi']
        volume = data['volume']
        beda = data['beda']
        keterangan = data['keterangan']

        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk memeriksa apakah user ID pengguna ada dalam database
        query = "SELECT * FROM cpo WHERE id = %s"
        values = (id,)
        cursor.execute(query, values)
        user = cursor.fetchone()

        if user:
            # Menjalankan query untuk mengubah data pengguna
            query = "UPDATE cpo SET tinggi = %s, volume = %s, beda = %s, keterangan = %s WHERE id = %s"
            values = (tinggi, volume, beda, keterangan, id)
            cursor.execute(query, values)

            # Melakukan commit perubahan ke database
            db.commit()

            response = {
                "message": "Data pengguna berhasil diubah!"
            }
        else:
            response = {
                "error": "User ID tidak ditemukan!"
            }

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify(response)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})



@app.route('/hapus_pengguna', methods=['DELETE'])
def hapus_pengguna():
    try:
        data = request.get_json()
        if 'user_id' in data:
            user_id = data['user_id']

            # Membuat koneksi ke database
            db = connect_to_database()

            # Membuat kursor
            cursor = db.cursor()

            # Menjalankan query untuk memeriksa apakah user ID pengguna ada dalam database
            query = "SELECT * FROM users WHERE user_id = %s"
            values = (user_id,)
            cursor.execute(query, values)
            user = cursor.fetchone()

            if user:
                # Menjalankan query untuk menghapus pengguna
                query = "DELETE FROM users WHERE user_id = %s"
                values = (user_id,)
                cursor.execute(query, values)

                # Melakukan commit perubahan ke database
                db.commit()

                response = {
                    "message": "Pengguna berhasil dihapus!"
                }
            else:
                response = {
                    "error": "User ID tidak ditemukan!"
                }

            # Menutup kursor dan koneksi database
            cursor.close()
            db.close()

            return jsonify(response)
        else:
            return jsonify({"error": "Data tidak lengkap"})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})

    
    
@app.route('/hapus_cpo', methods=['POST'])
def hapus_cpo():
    try:
        data = request.get_json()
        id = data['id']

        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk memeriksa apakah user ID pengguna ada dalam database
        query = "SELECT * FROM cpo WHERE id = %s"
        values = (id,)
        cursor.execute(query, values)
        user = cursor.fetchone()

        if user:
            # Menjalankan query untuk menghapus pengguna
            query = "DELETE FROM cpo WHERE id = %s"
            values = (id,)
            cursor.execute(query, values)

            # Melakukan commit perubahan ke database
            db.commit()

            response = {
                "message": "CPO berhasil dihapus!"
            }
        else:
            response = {
                "error": "CPO tidak ditemukan!"
            }

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify(response)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    

@app.route('/hapus_sounding', methods=['POST'])
def hapus_sounding():
    try:
        data = request.get_json()
        bulan = data['bulan']

        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk memeriksa apakah ada pengguna dengan data bulan yang sesuai
        query = "SELECT * FROM hasil_s WHERE MONTH(waktu) = %s"
        values = (bulan,)
        cursor.execute(query, values)
        users = cursor.fetchall()

        if users:
            # Menjalankan query untuk menghapus pengguna dengan data bulan yang sesuai
            query = "DELETE FROM hasil_s WHERE MONTH(waktu) = %s"
            values = (bulan,)
            cursor.execute(query, values)

            # Melakukan commit perubahan ke database
            db.commit()

            response = {
                "message": "Data sounding berhasil dihapus berdasarkan bulan!"
            }
        else:
            response = {
                "error": "Tidak ada data sounding yang sesuai dengan bulan yang diberikan!"
            }

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify(response)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
    
@app.route('/hapus_rendemen', methods=['POST'])
def hapus_rendemen():
    try:
        data = request.get_json()
        bulan = data['bulan']

        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk memeriksa apakah ada pengguna dengan data bulan yang sesuai
        query = "SELECT * FROM hasil_r WHERE MONTH(waktu) = %s"
        values = (bulan,)
        cursor.execute(query, values)
        users = cursor.fetchall()

        if users:
            # Menjalankan query untuk menghapus pengguna dengan data bulan yang sesuai
            query = "DELETE FROM hasil_r WHERE MONTH(waktu) = %s"
            values = (bulan,)
            cursor.execute(query, values)

            # Melakukan commit perubahan ke database
            db.commit()

            response = {
                "message": "Data rendemen berhasil dihapus berdasarkan bulan!"
            }
        else:
            response = {
                "error": "Tidak ada data rendemen yang sesuai dengan bulan yang diberikan!"
            }

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify(response)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})


    

@app.route('/tampilkan_data_pengguna', methods=['GET'])
def tampilkan_data_pengguna():
    try:
        # Membuat koneksi ke database
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sounding"
        )

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data pengguna
        query = "SELECT * FROM users"
        cursor.execute(query)

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Membuat list untuk menyimpan data pengguna
        data_pengguna = []

        # Menambahkan data ke dalam list
        for result in results:
            pengguna = {
                "user_id": result[0],
                "Nama": result[2],
                "Nik": result[3],
                "Password": result[4],
                "Jabatan": result[5]
            }
            data_pengguna.append(pengguna)

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify({"data_pengguna": data_pengguna})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
@app.route('/tampilkan_data_CPO', methods=['GET'])
def tampilkan_data_CPO():
    try:
        # Membuat koneksi ke database
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sounding"
        )

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data CPO
        query = "SELECT * FROM cpo"
        cursor.execute(query)

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Membuat list untuk menyimpan data CPO
        data_CPO = []

        # Menambahkan data ke dalam list
        for result in results:
            CPO = {
                "No": result[0],
                "Tinggi": result[1],
                "Volume": result[2],
                "Beda": result[3],
                "Keterangan": result[4]
            }
            data_CPO.append(CPO)

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify({"data_CPO": data_CPO})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    

@app.route('/tampilkan_data_sounding', methods=['GET'])
def tampilkan_data_sounding():
    try:
        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data sounding
        query = "SELECT id, waktu, nama, tangki, temperatur_suhu, tinggi, volume, hasil_sounding FROM hasil_s"
        cursor.execute(query)

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Membuat list untuk menyimpan data sounding
        data_sounding = []

        # Menambahkan data ke dalam list
        for result in results:
            sounding = {
                "id": result[0],
                "Waktu": result[1],
                "Nama": result[2],
                "Tangki": result[3],
                "Suhu": result[4],
                "Tinggi": result[5],
                "Volume": result[6],
                "hasil": result[7]
            }
            data_sounding.append(sounding)

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify({"data_sounding": data_sounding})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
    
@app.route('/tampilkan_data_rendemen', methods=['GET'])
def tampilkan_data_rendemen():
    try:
        # Membuat koneksi ke database
        db = connect_to_database()

        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data sounding
        query = "SELECT id,waktu, nama, pengiriman, stok_awal, jumlah_rebusan, TBS_olah, hasil_cpo, hasil_rendemen FROM hasil_r"
        cursor.execute(query)

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Membuat list untuk menyimpan data sounding
        data_rendemen = []

        # Menambahkan data ke dalam list
        for result in results:
            rendemen = {
                "id": result[0],
                "Waktu": result[1],
                "Nama": result[2],
                "Pengiriman": result[3],
                "Stok Awal": result[4],
                "Jumlah Rebusan": result[5],
                "TBS Olah": result[6],
                "Hasil CPO": result[7],
                "hasil": result[8]
            }
            data_rendemen.append(rendemen)

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return jsonify({"data_rendemen": data_rendemen})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})


# Definisikan fungsi untuk membuat koneksi ke database
def connect_to_database():
    # Gantikan bagian ini dengan kode koneksi ke database sesuai konfigurasi Anda
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sounding"
    )
    return db

# Fungsi untuk mengambil data berdasarkan tanggal dari database
def get_data_by_date_s(tanggal_input):
    try:
        # Membuat koneksi ke database
        db = connect_to_database()
        
        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data hasil berdasarkan tanggal
        query = "SELECT id, waktu, nama, tangki, temperatur_suhu, tinggi, volume, beda, hasil_sounding FROM hasil_s WHERE DATE(waktu) = %s"
        cursor.execute(query, (tanggal_input,))

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return results

    except mysql.connector.Error as err:
        return str(err)



@app.route('/download_hasil_sounding', methods=['POST', 'GET'])
def download_hasil_sounding():
    try:
        if request.method == 'POST':
            data = request.get_json()
            tanggal_input = data['tanggal']
        elif request.method == 'GET':
            tanggal_input = request.args.get('tanggal')
            
        # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
        results = get_data_by_date_s(tanggal_input)

        if isinstance(results, str):
            return jsonify({"error": results})

        # Membuat file PDF
        filename = f"hasil_sounding_{tanggal_input}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))

        # Membangun tabel dengan menggunakan data hasil
        headers = ["ID", "Waktu", "Nama", "Tangki", "Temperatur Suhu", "Tinggi", "Volume", "Beda", "Hasil Sounding"]
        table_data = [headers] + list(results)

        # Menentukan gaya tabel
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])

        # Mengatur gaya tabel
        table = Table(table_data)
        table.setStyle(style)

        # Menyiapkan elemen-elemen untuk ditambahkan ke dokumen PDF
        elements = []

        # Menambahkan judul laporan
        elements.append(Paragraph("LAPORAN HASIL SOUNDING YANG TERJADI DI PTPN IV PABATU", style=getSampleStyleSheet()['Title']))

        # Menambahkan tanggal pada dokumen PDF
        elements.append(Paragraph(f"Tanggal: {tanggal_input}", style=getSampleStyleSheet()['Heading2']))

        # Menambahkan tabel ke dokumen PDF
        elements.append(table)
        
        # Membuat dokumen PDF
        doc.build(elements)

        # Simpan file PDF dalam buffer BytesIO untuk disimpan dalam respons
        pdf_buffer = io.BytesIO()
        doc.save(pdf_buffer)
        pdf_buffer.seek(0)

        # Buat respons Flask dengan file PDF
        response = make_response(pdf_buffer.getvalue())

        # Atur header yang sesuai untuk download PDF
        response.headers['Content-Disposition'] = f'attachment; filename=hasil_sounding_{tanggal_input}.pdf'
        response.headers['Content-Type'] = 'application/pdf'

        return response

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
    
@app.route('/get_data_by_date_s', methods=['GET'])
def get_data_by_date_endpoint_s():
    tanggal_input = request.args.get('tanggal')

    # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
    results = get_data_by_date_s(tanggal_input)

    if isinstance(results, str):
        return jsonify({"error": results})

    # Menyiapkan list untuk menyimpan hasil data per row
    data_per_row = []

    # Mengubah setiap row hasil query menjadi dictionary
    for result in results:
        data_per_row.append({
            "waktu": result[1],
            "nama": result[2],
            "tangki": result[3],
            "temperatur_suhu": result[4],
            "tinggi": result[5],
            "volume": result[6],
            "beda": result[7],
            "hasil_sounding": result[8]
        })

    return jsonify({"error": "false", "data": data_per_row})

    
# Definisikan fungsi untuk membuat koneksi ke database
def connect_to_database():
    # Gantikan bagian ini dengan kode koneksi ke database sesuai konfigurasi Anda
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sounding"
    )
    return db

# Fungsi untuk mengambil data berdasarkan tanggal dari database
def get_data_by_date(tanggal_input):
    try:
        # Membuat koneksi ke database
        db = connect_to_database()
        
        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data hasil berdasarkan tanggal
        query = "SELECT id, waktu, nama, pengiriman, stok_awal, jumlah_rebusan, TBS_olah, hasil_cpo, hasil_rendemen FROM hasil_r WHERE DATE(waktu) = %s"
        cursor.execute(query, (tanggal_input,))

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return results

    except mysql.connector.Error as err:
        return str(err)


@app.route('/download_hasil_rendemen', methods=['POST', 'GET'])
def download_hasil_rendemen():
    try:
        if request.method == 'POST':
            data = request.get_json()
            tanggal_input = data['tanggal']
        elif request.method == 'GET':
            tanggal_input = request.args.get('tanggal')
            
        # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
        results = get_data_by_date(tanggal_input)

        if isinstance(results, str):
            return jsonify({"error": results})

        # Membuat file PDF
        filename = f"hasil_rendemen_{tanggal_input}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))

        # Membangun tabel dengan menggunakan data hasil
        headers = ["ID", "Waktu", "Nama", "Pengiriman", "Stok Awal", "Jumlah Rebusan", "TBS Olah", "Hasil CPO", "Hasil Rendemen"]
        table_data = [headers] + list(results)

        # Menentukan gaya tabel
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])

        # Mengatur gaya tabel
        table = Table(table_data)
        table.setStyle(style)

        # Menyiapkan elemen-elemen untuk ditambahkan ke dokumen PDF
        elements = []

        # Menambahkan judul laporan
        elements.append(Paragraph("LAPORAN HASIL RENDEMEN YANG TERJADI DI PTPN IV PABATU", style=getSampleStyleSheet()['Title']))

        # Menambahkan tanggal pada dokumen PDF
        elements.append(Paragraph(f"Tanggal: {tanggal_input}", style=getSampleStyleSheet()['Heading2']))

        # Menambahkan tabel ke dokumen PDF
        elements.append(table)
        
        # Membuat dokumen PDF
        doc.build(elements)

        # Simpan file PDF dalam buffer BytesIO untuk disimpan dalam respons
        pdf_buffer = io.BytesIO()
        doc.save(pdf_buffer)
        pdf_buffer.seek(0)

        # Buat respons Flask dengan file PDF
        response = make_response(pdf_buffer.getvalue())

        # Atur header yang sesuai untuk download PDF
        response.headers['Content-Disposition'] = f'attachment; filename=hasil_rendemen_{tanggal_input}.pdf'
        response.headers['Content-Type'] = 'application/pdf'

        return response

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
@app.route('/get_data_by_date', methods=['GET'])
def get_data_by_date_endpoint():
    tanggal_input = request.args.get('tanggal')

    # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
    results = get_data_by_date(tanggal_input)

    if isinstance(results, str):
        return jsonify({"error": results})

    # Mengubah hasil data menjadi format yang lebih sesuai jika diperlukan
    # Di sini, misalnya, hanya mengambil kolom "nama" dari hasil query
    waktu_data = [result[1] for result in results]
    nama_data = [result[2] for result in results]
    pengiriman_data = [result[3] for result in results]
    stok_data = [result[4] for result in results]
    rebusan_data = [result[5] for result in results]
    TBS_data = [result[6] for result in results]
    cpo_data = [result[7] for result in results]
    rendemen_data = [result[8] for result in results]

    return jsonify({
        "error":"false",
        "waktu": waktu_data,
        "nama": nama_data,
        "pengiriman": pengiriman_data,
        "stok_awal": stok_data,
        "jumlah_rebusan": rebusan_data,
        "TBS_olah": TBS_data,
        "hasil_cpo": cpo_data,
        "hasil_rendemen": rendemen_data
    })



#fungsi untuk mengambildata berdasarkan bulan di database
def get_data_by_bulan_s(bulan_input):
    try:
        
        # Membuat koneksi ke database
        db = connect_to_database()
        
        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data hasil berdasarkan tanggal
        query = "SELECT id, waktu, nama, tangki, temperatur_suhu, tinggi, volume, beda, hasil_sounding FROM hasil_s WHERE MONTH(waktu) = %s"
        cursor.execute(query, (bulan_input,))

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return results

    except mysql.connector.Error as err:
        return str(err)



@app.route('/hasil_sounding_admin', methods=['POST', 'GET'])
def hasil_sounding_admin():
    try:
        if request.method == 'POST':
            data = request.get_json()
            bulan_input = data['bulan']
        elif request.method == 'GET':
            bulan_input = request.args.get('bulan')
            
        # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
        results = get_data_by_bulan_s(bulan_input)

        if isinstance(results, str):
            return jsonify({"error": results})

        # Membuat file PDF
        filename = f"hasil_sounding_{bulan_input}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))

        # Membangun tabel dengan menggunakan data hasil
        headers = ["ID", "Waktu", "Nama", "Tangki", "Temperatur Suhu", "Tinggi", "Volume", "Beda", "Hasil Sounding"]
        table_data = [headers] + list(results)

        # Menentukan gaya tabel
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])

        # Mengatur gaya tabel
        table = Table(table_data)
        table.setStyle(style)

        # Menyiapkan elemen-elemen untuk ditambahkan ke dokumen PDF
        elements = []

        # Menambahkan judul laporan
        elements.append(Paragraph("LAPORAN HASIL SOUNDING YANG TERJADI DI PTPN IV PABATU", style=getSampleStyleSheet()['Title']))

        # Menambahkan tanggal pada dokumen PDF
        elements.append(Paragraph(f"Bulan: {bulan_input}", style=getSampleStyleSheet()['Heading2']))

        # Menambahkan tabel ke dokumen PDF
        elements.append(table)
        
        # Membuat dokumen PDF
        doc.build(elements)

        # Simpan file PDF dalam buffer BytesIO untuk disimpan dalam respons
        pdf_buffer = io.BytesIO()
        doc.save(pdf_buffer)
        pdf_buffer.seek(0)

        # Buat respons Flask dengan file PDF
        response = make_response(pdf_buffer.getvalue())

        # Atur header yang sesuai untuk download PDF
        response.headers['Content-Disposition'] = f'attachment; filename=hasil_sounding_admin_{bulan_input}.pdf'
        response.headers['Content-Type'] = 'application/pdf'

        return response

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
    
@app.route('/get_data_by_bulan_s', methods=['GET'])
def get_data_by_bulan_endpoint_s():
    bulan_input = request.args.get('bulan')

    # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
    results = get_data_by_bulan_s(bulan_input)

    if isinstance(results, str):
        return jsonify({"error": results})

    # Menyiapkan list untuk menyimpan hasil data per row
    data_per_row = []

    # Mengubah setiap row hasil query menjadi dictionary
    for result in results:
        data_per_row.append({
            "waktu": result[1],
            "nama": result[2],
            "tangki": result[3],
            "temperatur_suhu": result[4],
            "tinggi": result[5],
            "volume": result[6],
            "beda": result[7],
            "hasil_sounding": result[8]
        })

    return jsonify({"error": "false", "data": data_per_row})



#fungsi untuk mengambildata berdasarkan bulan di database
def get_data_by_bulan_r(bulan_input):
    try:
        
        # Membuat koneksi ke database
        db = connect_to_database()
        
        # Membuat kursor
        cursor = db.cursor()

        # Menjalankan query untuk mengambil data hasil berdasarkan tanggal
        query = "SELECT id, waktu, nama, pengiriman, stok_awal, jumlah_rebusan, TBS_olah, hasil_cpo, hasil_rendemen FROM hasil_r WHERE MONTH(waktu) = %s"
        cursor.execute(query, (bulan_input,))

        # Mendapatkan hasil query
        results = cursor.fetchall()

        # Menutup kursor dan koneksi database
        cursor.close()
        db.close()

        return results

    except mysql.connector.Error as err:
        return str(err)



@app.route('/hasil_rendemen_admin', methods=['POST', 'GET'])
def hasil_rendemen_admin():
    try:
        if request.method == 'POST':
            data = request.get_json()
            bulan_input = data['bulan']
        elif request.method == 'GET':
            bulan_input = request.args.get('bulan')
            
        # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
        results = get_data_by_bulan_r(bulan_input)

        if isinstance(results, str):
            return jsonify({"error": results})

        # Membuat file PDF
        filename = f"hasil_rendemen_{bulan_input}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))

        # Membangun tabel dengan menggunakan data hasil
        headers = ["ID", "Waktu", "Nama", "Pengiriman", "Stok Awal", "Jumlah Rebusan", "TBS Olah", "Hasil CPO", "Hasil Rendemen"]
        table_data = [headers] + list(results)

        # Menentukan gaya tabel
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])

        # Mengatur gaya tabel
        table = Table(table_data)
        table.setStyle(style)

        # Menyiapkan elemen-elemen untuk ditambahkan ke dokumen PDF
        elements = []

        # Menambahkan judul laporan
        elements.append(Paragraph("LAPORAN HASIL RENDEMEN YANG TERJADI DI PTPN IV PABATU", style=getSampleStyleSheet()['Title']))

        # Menambahkan tanggal pada dokumen PDF
        elements.append(Paragraph(f"Bulan: {bulan_input}", style=getSampleStyleSheet()['Heading2']))

        # Menambahkan tabel ke dokumen PDF
        elements.append(table)
        
        # Membuat dokumen PDF
        doc.build(elements)

        # Simpan file PDF dalam buffer BytesIO untuk disimpan dalam respons
        pdf_buffer = io.BytesIO()
        doc.save(pdf_buffer)
        pdf_buffer.seek(0)

        # Buat respons Flask dengan file PDF
        response = make_response(pdf_buffer.getvalue())

        # Atur header yang sesuai untuk download PDF
        response.headers['Content-Disposition'] = f'attachment; filename=hasil_rendemen_admin_{bulan_input}.pdf'
        response.headers['Content-Type'] = 'application/pdf'

        return response

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    
    
@app.route('/get_data_by_bulan_r', methods=['GET'])
def get_data_by_bulan_endpoint_r():
    bulan_input = request.args.get('bulan')

    # Memanggil fungsi untuk mendapatkan data berdasarkan tanggal
    results = get_data_by_bulan_r(bulan_input)

    if isinstance(results, str):
        return jsonify({"error": results})

    # Menyiapkan list untuk menyimpan hasil data per row
    data_per_row = []

    # Mengubah setiap row hasil query menjadi dictionary
    for result in results:
        data_per_row.append({
            "waktu": result[1],
            "nama": result[2],
            "pengiriman": result[3],
            "stok_awal": result[4],
            "jumlah_rebusan": result[5],
            "TBS_olah": result[6],
            "hasil_cpo": result[7],
            "hasil_rendemen": result[8]
        })

    return jsonify({"error": "false", "data": data_per_row})


    
@app.route('/edit-akun/<int:id>', methods=['PUT'])
def edit_akun(id):
    try:
        # Mendapatkan data dari body request
        data = request.get_json()
        new_nama = data['nama']
        new_nik = data['nik']
        new_password = data['password']
        new_jabatan = data['jabatan']

        # Membuat kursor database
        cursor = sounding.cursor()

        # Query SQL untuk mengubah data
        query = "UPDATE users SET nama = %s, nik = %s, password = %s, jabatan = %s WHERE user_id = %s"
        values = (new_nama, new_nik, new_password, new_jabatan, id)
        cursor.execute(query, values)

        # Melakukan perubahan pada database
        sounding.commit()

        # Menutup kursor
        cursor.close()

        return jsonify({'message': 'Data berhasil diubah'})

    except Exception as e:
        return jsonify({'message': 'Terjadi kesalahan', 'error': str(e)})
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105)

# Menutup koneksi database
cursor.close()
conn.close()


