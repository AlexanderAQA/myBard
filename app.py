from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_file, send_from_directory, abort, session
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import os
from models import db, User, Song
import random
from mutagen.flac import FLAC
import time
from flask_mail import Mail, Message
import string
import eyed3
import mutagen.mp3
import youtube_dl
from pytube import YouTube
from pydub import AudioSegment
from pydub.playback import play
import urllib.parse

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myappuser:mypassword@db:5432/myappdb' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:111@localhost:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#db = SQLAlchemy(app)
app.secret_key = 'your_secret_key'  

# You need to set a secret key for Flask session management
# Path to the directory containing the music files
#MUSIC_DIR = '/app/static/music/'
#YT_DIR = '/app/static/from_youtube/'
MUSIC_DIR = 'C:/Users/user/Documents/myBard/static/music'
YT_DIR = 'C:/Users/user/Documents/myBard/static/from_youtube'

bcrypt = Bcrypt(app)
# Configuring Flask-Mail to use Gmail's SMTP server
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
# Почта с которой будут отправляться письма
smtp_mail = 'al.wundt@gmail.com'
app.config['MAIL_USERNAME'] = smtp_mail
# Здесь должен быть пароль приложения от учетки gmail
app.config['MAIL_PASSWORD'] = 'lkiq ydce kmlm hxzq'
app.config['MAIL_DEFAULT_SENDER'] = smtp_mail

mail = Mail(app)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def generate_confirmation_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# пока не до конца реализовано
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

    # Generate and send confirmation code
        confirmation_code = generate_confirmation_code()
        session['confirmation_code'] = confirmation_code
        session['username'] = username
        session['password'] = password
        session['email'] = email

        # test
        #print ('Debug for confirmation code: ' + confirmation_code)
        
        msg = Message('Your Confirmation Code', sender=smtp_mail, recipients=[email])
        msg.body = f'Your confirmation code is {confirmation_code}.'
        mail.send(msg)

        flash('Please check your email for the confirmation code.')
        return redirect(url_for('confirm_email'))
    return render_template('register.html')

@app.route('/confirm_email', methods=['GET', 'POST'])
def confirm_email():
    if request.method == 'POST':
        entered_code = request.form['confirmation_code']
        if entered_code == session.get('confirmation_code'):
            # Retrieve the username and password from the session
            username = session.get('username')
            password = session.get('password')

            # Hash the password
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # Create a new user and save to the database
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            # Clear the session
            session.pop('confirmation_code', None)
            session.pop('username', None)
            session.pop('password', None)
            session.pop('email', None)

            flash('Email confirmed successfully!')
            time.sleep(1)
            return redirect(url_for('login'))
        else:
            flash('Invalid confirmation code. Please try again.')
            return redirect(url_for('confirm_email'))
    return render_template('confirm_email.html')


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('index.html')


# Function to download audio from YouTube and get video title
def download_audio(youtube_url, output_directory):
    try:
        yt = YouTube(youtube_url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        # Sanitize the title to be a valid filename
        sanitized_title = "".join(x for x in yt.title if x.isalnum() or x in "._- ")
        output_path = os.path.join(output_directory, f"{sanitized_title}.mp3")
        audio_stream.download(filename=output_path)
        print(f"Audio downloaded to {output_path}")
        return output_path, yt.title
    except Exception as e:
        print(f"Error downloading audio: {e}")
        raise e

@app.route('/download', methods=['POST'])
@login_required    
def download():
    try:
        youtube_link = request.form['youtube_url']
        output_directory = os.path.join(MUSIC_DIR)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        output_path, video_title = download_audio(youtube_link, output_directory)
        return render_template('index.html', audio_file=urllib.parse.quote(os.path.basename(output_path)), video_title=video_title)
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/song/<path:filename>', methods=['GET'])
def yt_song(filename):
    try:
        full_path = os.path.join(MUSIC_DIR, filename)
        if not os.path.exists(full_path):
            return jsonify({"error": "File not found"}), 404
        return send_file(full_path)
    except Exception as e:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        print(f"Error in /api/song/{filename} from {client_ip}: {e}")
        return jsonify({"error": str(e)}), 500

#
@app.route('/songs', methods=['POST'])
@login_required
def store_song():
    data = request.get_json()
    filename = data['filename']
    tags = data.get('tags', '')
    longitude = data.get('longitude', 0)
    artist = data.get('artist', '')
    new_song = Song(filename=filename, tags=tags, longitude_minutes=longitude, artist=artist)
    db.session.add(new_song)
    db.session.commit()
    return jsonify({'message': 'Song stored successfully'}), 201

#
@app.route('/songs', methods=['GET'])
@login_required
def get_songs():
    songs = Song.query.all()
    songs_list = [{'id': song.id, 'filename': song.filename, 'tags': song.tags, 'longitude': song.longitude_minutes, 'artist': song.artist} for song in songs]
    return jsonify(songs_list), 200

#
@app.route('/api/music', defaults={'path': ''})
@app.route('/api/music/<path:path>')
def get_music(path):
    full_path = os.path.join(MUSIC_DIR, path)
    if os.path.isdir(full_path):
        directories = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
        files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f)) and (f.endswith('.flac') or f.endswith('.mp3'))]
        return jsonify({"directories": directories, "files": files})
    else:
        return jsonify([])
#
@app.route('/api/song/<path:filename>', methods=['GET'])
def get_song(directory, filename):
    try:
        if not os.path.exists(full_path):
            full_path = os.path.join(MUSIC_DIR, filename)
            return jsonify({"error": "File not found"}), 404

        return send_file(full_path)
    except Exception as e:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        print(f"Error in /api/song/{directory}/{filename} from {client_ip}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/static/from_youtube/<path:filename>', methods=['GET'])
def yt_files(filename):
    try:
        full_path = os.path.join(MUSIC_DIR, filename)
        if not os.path.exists(full_path):
            return jsonify({"error": "File not found"}), 404
        return send_file(full_path)
    except Exception as e:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        print(f"Error in /static/from_youtube/{filename} from {client_ip}: {e}")
        return jsonify({"error": str(e)}), 500

#
@app.route('/static/css/<path:filename>')
def static_css(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'css'), filename)

#
@app.route('/static/js/<path:filename>')
def static_js(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'js'), filename)

# Модуль для выбора случайной песни из списка файлов
def get_random_song(MUSIC_DIR):
    music_files = []
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
            if file.endswith('.flac') or file.endswith('.mp3'):
                music_files.append(os.path.join(root, file))

    if not music_files:
        return None

    return random.choice(music_files)

# Случайная песня
@app.route('/api/random', methods=['GET'])
def random_song_endpoint():
    try:
        random_song = get_random_song(MUSIC_DIR)
        if random_song:
            return jsonify({"file": random_song}), 200
        else:
            return jsonify({"error": "No .flac files found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Возвращает на запрос случайную песню
@app.route('/api/song/<path:filename>', methods=['GET'])
def serve_song(filename):
    return send_from_directory(MUSIC_DIR, filename)
    
# Плейлист из случайных песен (RandomWave)
@app.route('/api/wave/random', methods=['GET'])
def get_random_wave():
    try:
        if not os.path.isdir(MUSIC_DIR):
            raise Exception("Music directory not found")
        
        music_files = []
        for root, dirs, files in os.walk(MUSIC_DIR):
            for file in files:
                if file.endswith('.flac') or file.endswith('.mp3'):
                    music_files.append(os.path.join(root, file))
        
        if not music_files:
            raise Exception("No songs found in the music directory")
        
        random_playlist = generate_random_playlist(music_files)
        return jsonify({"songs": random_playlist})
    except Exception as e:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        print(f"Error in /api/wave/random from {client_ip}: {e}")
        return jsonify({"error": str(e)}), 500

def generate_random_playlist(songs):
    playlist = []
    total_duration = 0
    max_duration = 7200  # 2 hours in seconds

    while total_duration < max_duration and songs:
        random_index = random.randint(0, len(songs) - 1)
        selected_song = songs[random_index]
        song_duration = get_song_duration(selected_song)
        
        if total_duration + song_duration <= max_duration:
            playlist.append({"path": selected_song, "duration": song_duration})
            total_duration += song_duration
            songs.pop(random_index)
        else:
            break

    return playlist

def get_song_duration(song):
    try:
        if song.endswith('.flac'):
            audio = eyed3.load(song)
            return int(audio.info.time_secs)
        elif song.endswith('.mp3'):
            audio = mutagen.mp3.MP3(song)
            return int(audio.info.length)
        else:
            raise Exception("Unsupported file format")
    except Exception as e:
        print(f"Error getting duration for {song}: {e}")
        return 0

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)