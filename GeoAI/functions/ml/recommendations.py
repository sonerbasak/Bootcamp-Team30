import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import math
import random
import logging 
import json


from functions.database.connections import get_db_connection, settings
from functions.database.queries import get_user_category_success_rates, get_all_users_category_data, get_user_by_id


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_cosine_similarity(vec1, vec2):
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(v**2 for v in vec1))
    magnitude2 = math.sqrt(sum(v**2 for v in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def get_recommended_friends_kmeans(current_user_id: int, num_recommendations: int = 5, num_clusters: int = 5):
    """
    Kullanıcının quiz kategori başarılarına göre K-Means kümeleme kullanarak arkadaş önerileri sunar.
    Test amaçlı olarak, benzerlik oranı düşük olsa bile belirli sayıda öneri sunmayı hedefler.
    """
    all_users_category_vectors, all_categories = get_all_users_category_data()
    
    
    if current_user_id not in all_users_category_vectors or len(all_users_category_vectors) <= 1:
        logging.info(f"K-Means: Mevcut kullanıcı ({current_user_id}) için veri yok veya yeterli başka kullanıcı yok. Öneri yapılamıyor.")
        return []


    user_ids = list(all_users_category_vectors.keys())
    user_vectors = np.array(list(all_users_category_vectors.values()))


    if len(all_users_category_vectors) >= num_clusters and len(all_users_category_vectors) > 1:
        try:

            scaler = StandardScaler()
            scaled_user_vectors = scaler.fit_transform(user_vectors)


            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
            kmeans.fit(scaled_user_vectors)


            cluster_labels = kmeans.labels_
            user_cluster_map = {user_ids[i]: cluster_labels[i] for i in range(len(user_ids))}


            current_user_cluster = user_cluster_map[current_user_id]
            

            friends_in_same_cluster = [
                uid for uid, cluster in user_cluster_map.items()
                if cluster == current_user_cluster and uid != current_user_id
            ]
            

            if friends_in_same_cluster:
                with get_db_connection(settings.USERS_DATABASE_FILE) as user_conn:
                    user_cursor = user_conn.cursor()
                    
                    recommended_users_info = []
                    for uid in friends_in_same_cluster:

                        user_info = get_user_by_id(uid)
                        if user_info:

                            user_cursor.execute("SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?", (current_user_id, user_info["id"]))
                            already_following = user_cursor.fetchone() is not None

                            if not already_following:
                                recommended_users_info.append({
                                    "id": uid,
                                    "username": user_info["username"],
                                    "profile_picture_url": user_info.get("profile_picture_url", "/static/images/sample_user.png"),
                                    "similarity": "Aynı Kümede"
                                })
                    

                if len(recommended_users_info) >= num_recommendations:
                    return random.sample(recommended_users_info, min(num_recommendations, len(recommended_users_info)))

        except Exception as e:
            logging.error(f"K-Means kümeleme hatası: {e}. Kosinüs Benzerliği tabanlı fallback uygulanıyor.")



    logging.info("K-Means ile yeterli öneri bulunamadı veya kümeleme mümkün değil. Kosinüs Benzerliği tabanlı fallback uygulanıyor.")
    
    current_user_vector = all_users_category_vectors.get(current_user_id)
    if not current_user_vector:
        logging.warning(f"Kosinüs Benzerliği: Mevcut kullanıcı ({current_user_id}) için kategori vektörü bulunamadı.")
        return []

    similarities = []
    other_user_ids = [uid for uid in user_ids if uid != current_user_id] # Kendi kullanıcı ID'sini hariç tut


    with get_db_connection(settings.USERS_DATABASE_FILE) as user_conn:
        user_cursor = user_conn.cursor()
        
        for user_id in other_user_ids:
            user_vector = all_users_category_vectors.get(user_id)
            if user_vector:
                user_cursor.execute("SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?", (current_user_id, user_id))
                already_following = user_cursor.fetchone() is not None

                if not already_following:
                    similarity = calculate_cosine_similarity(current_user_vector, user_vector) 
                    similarities.append({"user_id": user_id, "similarity": similarity})


    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    

    top_recommendations_ids = similarities[:num_recommendations]

    recommended_users_info = []

    with get_db_connection(settings.USERS_DATABASE_FILE) as user_conn:
        user_cursor = user_conn.cursor()
        for rec in top_recommendations_ids:
            user_cursor.execute("SELECT username, profile_picture_url FROM users WHERE id = ?", (rec["user_id"],))
            user_row = user_cursor.fetchone()
            if user_row:
                recommended_users_info.append({
                    "id": rec["user_id"],
                    "username": user_row[0],
                    "profile_picture_url": user_row[1] or "/static/images/sample_user.png",
                    "similarity": round(rec["similarity"] * 100, 2)
                })

    return recommended_users_info