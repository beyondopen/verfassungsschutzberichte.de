release: flask init-db && flask clear-cache
web: bash -c 'flask create-zips & exec gunicorn app:app --workers=5'
