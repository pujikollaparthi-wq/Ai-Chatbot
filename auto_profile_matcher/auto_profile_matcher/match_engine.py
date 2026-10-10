from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
nltk.download('punkt', quiet=True)

# Example job descriptions (replace with your DB)
JOB_ROLES = [
    {"role": "Data Scientist", "desc": "machine learning, python, data analysis, statistics, pandas, scikit-learn"},
    {"role": "Backend Developer", "desc": "python, flask, django, rest api, databases, sql"},
    {"role": "Frontend Developer", "desc": "javascript, react, html, css, web UI, frontend"},
    {"role": "DevOps Engineer", "desc": "aws, docker, kubernetes, ci cd, monitoring, terraform"},
    {"role": "QA Engineer", "desc": "testing, selenium, automation, test cases, pytest"}
]

def best_matches(profile_text, top_k=3):
    """
    profile_text: combined user skills + resume text
    returns top_k matches as list of tuples (role, score)
    """
    docs = [job["desc"] for job in JOB_ROLES]
    docs.append(profile_text)  # last is user
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf = vectorizer.fit_transform(docs)  # shape: (len(docs), n_features)
    user_vec = tfidf[-1]
    job_vecs = tfidf[:-1]
    sims = cosine_similarity(user_vec, job_vecs).flatten()  # similarity to each job
    ranked = sorted(enumerate(sims), key=lambda x: x[1], reverse=True)
    results = []
    for idx, score in ranked[:top_k]:
        results.append((JOB_ROLES[idx]["role"], float(score)))
    return results
