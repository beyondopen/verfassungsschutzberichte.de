release: flask init-db && flask clear-cache
web: flask create-zips & gunicorn app:app --workers=5
