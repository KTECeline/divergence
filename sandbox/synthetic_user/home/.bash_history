cd /workspace/project
source .venv/bin/activate
pip install -r requirements.txt
python src/app.py --port 8000
git pull origin main
aws s3 ls s3://northwind-demo-backups/
ssh staging
vim .env
pytest -q
git commit -am "fix invoice rounding"
