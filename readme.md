# Update your package list
sudo apt-get update

# Install nginx
sudo apt-get install nginx

# Install gunicorn using pip
pip install gunicorn

# Run gunicorn (replace 'update_samba_passwords:app' with your actual app)
gunicorn -w 4 update_samba_passwords:app

# Create a new nginx configuration (replace 'yourdomain.com' with your actual domain)
echo "server {
    listen 80;
    server_name yourdomain.com;
    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/update_samba_passwords.sock;
    }
}" | sudo tee /etc/nginx/sites-available/yourdomain.com

# Create a symbolic link to enable the new configuration
sudo ln -s /etc/nginx/sites-available/yourdomain.com /etc/nginx/sites-enabled/

# Test the nginx configuration
sudo nginx -t

# Restart nginx to apply the changes
sudo systemctl restart nginx

# Allow nginx through the firewall (if you have ufw enabled)
sudo ufw allow 'Nginx Full'

# Start your Flask app with gunicorn
gunicorn --bind unix:/tmp/update_samba_passwords.sock -m 007 update_samba_passwords:app


# Still need to get SSL Certificate and setup systemd to manage Gunicorn to start at boot and restart