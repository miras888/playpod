from flask import Flask, render_template, request, redirect, session, jsonify, url_for, flash
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, apology
import os
from datetime import datetime

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///playpod.db")





























































@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def index():
    """Show home page with albums and featured content"""
    albums = db.execute("SELECT * FROM albums")

    featured_songs = db.execute(
        "SELECT songs.*, albums.title as album_title FROM songs JOIN albums ON songs.album_id = albums.id ORDER BY RANDOM() LIMIT 5"
    )

    genres = db.execute("SELECT DISTINCT genre FROM songs ORDER BY genre")

    return render_template("index.html", albums=albums, featured_songs=featured_songs, genres=genres)

@app.route("/all_songs")
def all_songs():
    """Show all songs with favorite status for logged-in user"""

    user_id = session.get("user_id")

    if user_id:
            songs = db.execute(
            "SELECT songs.*, albums.title AS album_title, "
            "CASE WHEN favorites.song_id IS NOT NULL THEN 1 ELSE 0 END AS is_favorite "
            "FROM songs "
            "JOIN albums ON songs.album_id = albums.id "
            "LEFT JOIN favorites ON songs.id = favorites.song_id AND favorites.user_id = ? "
            "ORDER BY songs.title",
            user_id
        )
    else:
        songs = db.execute(
            "SELECT songs.*, albums.title AS album_title, 0 AS is_favorite "
            "FROM songs "
            "JOIN albums ON songs.album_id = albums.id "
            "ORDER BY songs.title"
        )

    genres = db.execute("SELECT DISTINCT genre FROM songs ORDER BY genre")

    return render_template("all_songs.html", songs=songs, genres=genres)

@app.route("/album/<int:album_id>")
def album(album_id):
    """Show specific album and its songs"""

    album = db.execute("SELECT * FROM albums WHERE id = ?", album_id)
    if not album:
        return apology("Album not found", 404)

    songs = db.execute(
        "SELECT * FROM songs WHERE album_id = ? ORDER BY song_number", album_id
    )

    genres = db.execute("SELECT DISTINCT genre FROM songs ORDER BY genre")

    return render_template("album.html", album=album[0], songs=songs, genres=genres)

@app.route("/song/<int:song_id>")
def song(song_id):
    """Get song info for the player"""
    song = db.execute(
        "SELECT songs.*, albums.title as album_title, albums.cover as album_cover FROM songs JOIN albums ON songs.album_id = albums.id WHERE songs.id = ?",
        song_id
    )

    if not song:
        return apology("Song not found", 404)

    if "user_id" in session:
        
        db.execute(
            "INSERT INTO history (user_id, song_id, listened_at) VALUES (?, ?, ?)",
            session["user_id"], song_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )


    is_favorite = False
    if "user_id" in session:
        favorite = db.execute(
            "SELECT * FROM favorites WHERE user_id = ? AND song_id = ?",
            session["user_id"], song_id
        )
        is_favorite = len(favorite) > 0


    suggested_songs = db.execute(
        "SELECT songs.*, albums.title as album_title FROM songs JOIN albums ON songs.album_id = albums.id WHERE songs.genre = ? AND songs.id != ? ORDER BY RANDOM() LIMIT 5",
        song[0]["genre"], song_id
    )

    return render_template("player.html", song=song[0], is_favorite=is_favorite, suggested_songs=suggested_songs)

@app.route("/search")
def search():
    """Search for songs or artists"""
    query = request.args.get("q", "")

    if not query:
        return redirect("/")

    songs = db.execute(
        "SELECT songs.*, albums.title as album_title FROM songs JOIN albums ON songs.album_id = albums.id WHERE songs.title LIKE ? OR songs.artist LIKE ? ORDER BY songs.title",
        f"%{query}%", f"%{query}%"
    )

    albums = db.execute(
        "SELECT * FROM albums WHERE title LIKE ? OR artist LIKE ? ORDER BY title",
        f"%{query}%", f"%{query}%"
    )


    genres = db.execute("SELECT DISTINCT genre FROM songs ORDER BY genre")

    return render_template("search.html", songs=songs, albums=albums, query=query, genres=genres)

@app.route("/filter")
def filter():
    """Filter songs by genre"""
    genre = request.args.get("genre", "")
    album_id = request.args.get("album_id")

    if album_id:

        songs = db.execute(
            "SELECT * FROM songs WHERE album_id = ? AND genre = ? ORDER BY song_number",
            album_id, genre
        )
        album = db.execute("SELECT * FROM albums WHERE id = ?", album_id)[0]
        return render_template("album.html", album=album, songs=songs, selected_genre=genre)
    else:

        songs = db.execute(
            "SELECT songs.*, albums.title as album_title FROM songs JOIN albums ON songs.album_id = albums.id WHERE genre = ? ORDER BY songs.title",
            genre
        )
        genres = db.execute("SELECT DISTINCT genre FROM songs ORDER BY genre")
        return render_template("filtered.html", songs=songs, selected_genre=genre, genres=genres)

@app.route("/favorites", methods=["GET", "POST"])
@login_required
def favorites():
    """Manage favorite songs"""
    if request.method == "POST":
        song_id = request.form.get("song_id")
        action = request.form.get("action")

        if not song_id or not action:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "Missing song ID or action"}), 400
            return apology("Missing song ID or action", 400)

        try:
            if action == "add":
                
                existing = db.execute(
                    "SELECT 1 FROM favorites WHERE user_id = ? AND song_id = ?",
                    session["user_id"], song_id
                )
                if not existing:
                    db.execute(
                        "INSERT INTO favorites (user_id, song_id, added_at) VALUES (?, ?, ?)",
                        session["user_id"], song_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
            elif action == "remove":
                db.execute(
                    "DELETE FROM favorites WHERE user_id = ? AND song_id = ?",
                    session["user_id"], song_id
                )
            else:
                return jsonify({"error": "Invalid action"}), 400

            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True, "action": action})
            
            return redirect(request.referrer or "/favorites")

        except Exception as e:
            print(f"Error in favorites route: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "Database operation failed"}), 500
            flash("An error occurred", "danger")
            return redirect(request.referrer or "/favorites")

    favorite_songs = db.execute(
        "SELECT songs.*, albums.title as album_title, favorites.added_at "
        "FROM favorites JOIN songs ON favorites.song_id = songs.id "
        "JOIN albums ON songs.album_id = albums.id "
        "WHERE favorites.user_id = ? ORDER BY favorites.added_at DESC",
        session["user_id"]
    )
    return render_template("favorites.html", songs=favorite_songs)

@app.route("/create_playlist", methods=["GET", "POST"])
@login_required
def create_new_playlist():
    """Show form to create a new playlist by name"""
    if request.method == "POST":
        playlist_name = request.form.get("playlist_name")

        if not playlist_name or not playlist_name.strip():
            flash("Playlist name cannot be empty.", "warning")
            return render_template("create_new_playlist.html")

        
        existing_playlist = db.execute(
            "SELECT id FROM playlists WHERE user_id = ? AND title = ?",
            session["user_id"], playlist_name.strip()
        )
        if existing_playlist:
             flash("You already have a playlist with this name.", "warning")
             return render_template("create_new_playlist.html")


        
        try:
            db.execute(
                "INSERT INTO playlists (user_id, title, created_at) VALUES (?, ?, ?)",
                session["user_id"], playlist_name.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            flash(f"Playlist '{playlist_name.strip()}' created successfully!", "success")
            return redirect("/playlists") 
        except Exception as e:
             print("Error creating playlist:", e)
             flash("Failed to create playlist. Please try again.", "danger")
             return render_template("create_new_playlist.html")


    
    return render_template("create_new_playlist.html")




@app.route("/add_to_playlist/<int:song_id>")
@login_required
def add_to_playlist(song_id):
    """Show form to add a song to an EXISTING playlist"""

    
    song = db.execute("SELECT songs.*, albums.title as album_title FROM songs JOIN albums ON songs.album_id = albums.id WHERE songs.id = ?", song_id)

    if not song:
        return apology("Song not found", 404)

    
    user_playlists = db.execute("SELECT id, title FROM playlists WHERE user_id = ? ORDER BY created_at DESC", session["user_id"])

    
    
    if not user_playlists:
        flash("You need to create a playlist first.", "info")
        return redirect("/create_playlist") 


    return render_template("add_to_playlist.html", song=song[0], playlists=user_playlists)



@app.route("/handle_add_to_playlist", methods=["POST"])
@login_required
def handle_add_to_playlist():
    """Handle adding a song to a selected EXISTING playlist"""
    song_id = request.form.get("song_id")
    playlist_id = request.form.get("playlist_id") 


    if not song_id or not playlist_id:
        flash("Missing song or playlist information.", "danger")
        
        return redirect(request.referrer or "/all_songs")

    try:
        target_playlist_id = int(playlist_id)

        
        existing_playlist = db.execute(
            "SELECT title FROM playlists WHERE id = ? AND user_id = ?",
            target_playlist_id, session["user_id"]
        )
        if not existing_playlist:
            flash("Playlist not found or not authorized.", "danger")
            return redirect(request.referrer or "/all_songs")

        playlist_name_for_message = existing_playlist[0]["title"]

        
        existing_song_in_playlist = db.execute(
            "SELECT id FROM playlist_songs WHERE playlist_id = ? AND song_id = ?",
            target_playlist_id, song_id
        )

        if existing_song_in_playlist:
            flash(f"Song is already in '{playlist_name_for_message}'.", "info")
        else:
            
            db.execute(
                "INSERT INTO playlist_songs (playlist_id, song_id) VALUES (?, ?)",
                target_playlist_id, song_id
            )
            flash(f"Song added to '{playlist_name_for_message}' successfully!", "success")


        
        return redirect(url_for('playlist', playlist_id=target_playlist_id))

    except Exception as e:
        print("Error handling add song to existing playlist:", e)
        flash("Failed to add song to playlist. Please try again.", "danger")
        
        return redirect(request.referrer or "/all_songs")



@app.route("/history")
@login_required 
def history():
    """Show listening history"""

    
    history_items = db.execute(
        "SELECT history.id, songs.id AS song_id, songs.title AS song_title, songs.artist AS artist_name, albums.title AS album_title, albums.cover AS album_cover, history.listened_at "
        "FROM history JOIN songs ON history.song_id = songs.id "
        "LEFT JOIN albums ON songs.album_id = albums.id " 
        "WHERE history.user_id = ? ORDER BY history.listened_at DESC", 
        session["user_id"]
    )
    
    grouped_history = {}
    for item in history_items:
        listened_datetime = datetime.strptime(item["listened_at"], "%Y-%m-%d %H:%M:%S")   
        date_str = listened_datetime.strftime("%Y-%m-%d")
        item["listened_time_formatted"] = listened_datetime.strftime("%H:%M")

        if date_str not in grouped_history:
            grouped_history[date_str] = []
        grouped_history[date_str].append(item)
    
    return render_template("history.html", grouped_history=grouped_history)


@app.route("/playlists")
@login_required
def playlists():
    """Show user's playlists"""
    user_playlists = db.execute(
        "SELECT playlists.*, COUNT(playlist_songs.song_id) as song_count FROM playlists LEFT JOIN playlist_songs ON playlists.id = playlist_songs.playlist_id WHERE playlists.user_id = ? GROUP BY playlists.id ORDER BY playlists.created_at DESC",
        session["user_id"]
    )

    return render_template("playlists.html", playlists=user_playlists)

@app.route("/playlist/<int:playlist_id>")
def playlist(playlist_id):
    """Show specific playlist and its songs"""
    playlist = db.execute("SELECT * FROM playlists WHERE id = ?", playlist_id)
    if not playlist:
        return apology("Playlist not found", 404)

    if "user_id" not in session or (session["user_id"] != playlist[0]["user_id"] and not playlist[0]["is_public"]):
        return apology("You don't have permission to view this playlist", 403)

    songs = db.execute(
        "SELECT songs.*, albums.title as album_title, albums.cover as album_cover FROM playlist_songs JOIN songs ON playlist_songs.song_id = songs.id JOIN albums ON songs.album_id = albums.id WHERE playlist_songs.playlist_id = ? ORDER BY playlist_songs.id",
        playlist_id
    )

    return render_template("playlist.html", playlist=playlist[0], songs=songs)

@app.route("/edit_playlist/<int:playlist_id>", methods=["GET", "POST"])
@login_required
def edit_playlist(playlist_id):
    """Edit playlist details and songs"""

    playlist = db.execute("SELECT * FROM playlists WHERE id = ?", playlist_id)
    if not playlist or playlist[0]["user_id"] != session["user_id"]:
        return apology("Playlist not found or unauthorized", 403)

    if request.method == "POST":
        title = request.form.get("title", playlist[0]["title"])
        is_public = "is_public" in request.form

        db.execute(
            "UPDATE playlists SET title = ?, is_public = ? WHERE id = ?",
            title, is_public, playlist_id
        )

        songs_to_remove = request.form.getlist("remove_song")
        
        valid_song_ids = [int(song_id) for song_id in songs_to_remove if song_id.isdigit()]
        if valid_song_ids:
            placeholders = ", ".join("?" * len(valid_song_ids))
            db.execute(
                 f"DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id IN ({placeholders})",
                 playlist_id, *valid_song_ids
             )

        return redirect(f"/playlist/{playlist_id}")

    songs = db.execute(
        "SELECT songs.*, albums.title as album_title FROM playlist_songs JOIN songs ON playlist_songs.song_id = songs.id JOIN albums ON songs.album_id = albums.id WHERE playlist_songs.playlist_id = ? ORDER BY playlist_songs.id",
        playlist_id
    )

    return render_template("edit_playlist.html", playlist=playlist[0], songs=songs)


@app.route("/remove_from_playlist", methods=["POST"])
@login_required
def remove_from_playlist():
    """Remove a song from a playlist"""
    playlist_id = request.form.get("playlist_id")
    song_id = request.form.get("song_id")

    if not playlist_id or not song_id:
        flash("Missing playlist or song information.", "danger")
        return redirect(request.referrer or "/playlists")

    try:
        
        playlist = db.execute("SELECT id FROM playlists WHERE id = ? AND user_id = ?", playlist_id, session["user_id"])
        if not playlist:
             flash("Playlist not found or not authorized.", "danger")
             return redirect(request.referrer or "/playlists")

        
        deleted_rows = db.execute(
            "DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?",
            playlist_id, song_id
        )

        if deleted_rows > 0:
            flash("Song removed from playlist.", "success")
        else:
            flash("Song was not found in the playlist.", "info")


    except Exception as e:
        print("Error removing song from playlist:", e)
        flash("Failed to remove song from playlist. Please try again.", "danger")

    
    return redirect(url_for('playlist', playlist_id=playlist_id))



@app.route("/delete_playlist/<int:playlist_id>", methods=["POST"])
@login_required
def delete_playlist(playlist_id):
    """Delete an entire playlist"""

    try:
        
        playlist = db.execute("SELECT id FROM playlists WHERE id = ? AND user_id = ?", playlist_id, session["user_id"])
        if not playlist:
             flash("Playlist not found or not authorized.", "danger")
             return redirect("/playlists") 

        
        
        db.execute("BEGIN TRANSACTION;")

        
        db.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", playlist_id)
        print(f"Deleted songs for playlist ID {playlist_id} from playlist_songs.") 

        
        deleted_playlists = db.execute("DELETE FROM playlists WHERE id = ?", playlist_id)
        print(f"Deleted playlist with ID {playlist_id}.") 

        if deleted_playlists > 0:
            db.execute("COMMIT;")
            flash("Playlist deleted successfully.", "success")
            return redirect("/playlists") 
        else:
            
            
            db.execute("ROLLBACK;")
            flash("Playlist not found or could not be deleted.", "danger")
            return redirect("/playlists")


    except Exception as e:
        
        try:
            db.execute("ROLLBACK;")
        except Exception as rollback_error:
            print("Error during rollback after delete playlist:", rollback_error)

        print("Error deleting playlist:", e)
        flash("Failed to delete playlist. Please try again.", "danger")
        
        
        return redirect("/playlists")
    
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("Must provide username")
        elif not password:
            return apology("Must provide password")
        elif password != confirmation:
            return apology("Passwords must match")

        if len(password) < 8:
            return apology("Password must be at least 8 characters long")

        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return apology("Username already exists")

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        
        new_user = db.execute("SELECT id, username FROM users WHERE username = ?", username) 
        if new_user:
            session["user_id"] = new_user[0]["id"]
            session["username"] = new_user[0]["username"]
        else:
             
             flash("Registration successful, but could not log in automatically. Please log in.", "warning")
             return redirect("/login")

        return redirect("/")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return apology("Must provide username")
        elif not password:
            return apology("Must provide password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid username and/or password")

        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

if __name__ == "__main__":    
    app.run(debug=True, host='0.0.0.0')