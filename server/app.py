from flask import Flask, jsonify, request
from flask_cors import CORS
import random
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import uuid
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from azure.data.tables import TableServiceClient

load_dotenv()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if not connection_string:
    raise RuntimeError("Azure Storage connection string is missing.")

table_service = TableServiceClient.from_connection_string(
    conn_str=connection_string
)

movies_table = table_service.get_table_client("Movies")
submissions_table = table_service.get_table_client("Submissions")

app = Flask(__name__)
CORS(app)

movies = {
    "action": [
        "The Dark Knight",
        "Gladiator",
        "Mad Max: Fury Road",
        "John Wick"
    ],
    "comedy": [
        "Superbad",
        "The Hangover",
        "Step Brothers",
        "The Truman Show"
    ],
    "horror": [
        "The Shining",
        "Get Out",
        "The Conjuring",
        "A Quiet Place"
    ],
    "sci-fi": [
        "Interstellar",
        "Inception",
        "The Matrix",
        "Arrival"
    ]
}

def seed_movies():
    for genre, titles in movies.items():
        for index, title in enumerate(titles):
            movies_table.upsert_entity({
                "PartitionKey": genre,
                "RowKey": str(index),
                "title": title
            })


@app.route("/api/setup", methods=["POST"])
def setup_database():
    seed_movies()
    return jsonify({"message": "Movies added to Azure database!"})


@app.route("/api/movie", methods=["GET"])
def get_movie():
    movie_records = list(movies_table.list_entities())

    if not movie_records:
        return jsonify({"error": "No movies found in database"}), 404

    selected_movie = random.choice(movie_records)

    return jsonify({
        "movie": selected_movie["title"]
    })

@app.route("/api/recommend", methods=["POST"])
def recommend_movie():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON data"}), 400

    genre = data.get("genre")

    # Server-side validation
    allowed_genres = {"action", "comedy", "horror", "sci-fi"}

    if not isinstance(genre, str):
        return jsonify({"error": "Genre must be text"}), 400

    genre = genre.strip().lower()

    if genre not in allowed_genres:
        return jsonify({"error": "Invalid genre"}), 400

    movie_records = list(
        movies_table.query_entities(
            query_filter="PartitionKey eq @genre",
            parameters={"genre": genre}
        )
    )

    if not movie_records:
        return jsonify({"error": "No movies found"}), 404

    selected_movie = random.choice(movie_records)

    # Save the user's genre selection to Azure
    submissions_table.create_entity({
        "PartitionKey": "recommendations",
        "RowKey": str(uuid.uuid4()),
        "genre": genre,
        "movie": selected_movie["title"],
        "submitted_at": datetime.now(timezone.utc).isoformat()
    })

    return jsonify({
        "movie": selected_movie["title"],
        "genre": genre
    })

@app.route("/api/history", methods=["GET"])
def get_history():
    records = list(submissions_table.list_entities())

    records.sort(
        key=lambda record: record.get("submitted_at", ""),
        reverse=True
    )

    history = [
        {
            "genre": record["genre"],
            "movie": record["movie"],
            "submitted_at": record["submitted_at"]
        }
        for record in records[:10]
    ]

    return jsonify({"history": history})

@app.route("/api/auth/google", methods=["POST"])
def google_login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    credential = data.get("credential")

    if not isinstance(credential, str) or not credential:
        return jsonify({"error": "Missing Google credential"}), 400

    google_client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not google_client_id:
        return jsonify({"error": "Google login is not configured"}), 500

    try:
        user_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            google_client_id
        )

        if user_info.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com"
        ):
            return jsonify({"error": "Invalid token issuer"}), 401

        if not user_info.get("sub"):
            return jsonify({"error": "Invalid user identity"}), 401

        if not user_info.get("email_verified"):
            return jsonify({"error": "Google email is not verified"}), 401

        return jsonify({
            "name": user_info.get("name", "Movie Fan"),
            "email": user_info.get("email", "")
        })

    except ValueError:
        return jsonify({"error": "Invalid or expired Google token"}), 401

if __name__ == "__main__":
    app.run(debug=True)