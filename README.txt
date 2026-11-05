ROOMFINDER - WINDOWS SETUP

1) Extract this ZIP and open the RoomFinder_Complete folder in VS Code.
2) Open Terminal in VS Code and run these commands one by one:

   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py

3) Open http://127.0.0.1:5000

OWNER:
- Click List Property / Owner Login.
- Register with name, mobile number and password.
- Login to add listings and delete only your own listings.

STUDENT:
- No login needed. Search approved rooms and view room details.

ADMIN:
- Open http://127.0.0.1:5000/admin
- Username: admin
- Password: ChangeMe123!
- Approve or reject owner-submitted listings.
- Change the default admin password before any public deployment.

NOTES:
- Only approved rooms appear in public search.
- Exact address and owner contact appear on the approved room detail page.
- Photos are stored in static/uploads; database is created automatically.
- For real public hosting, configure a strong ROOMFINDER_SECRET, change the
  admin password, enable HTTPS and add CSRF protection.
