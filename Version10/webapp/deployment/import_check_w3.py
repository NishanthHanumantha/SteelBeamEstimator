"""Critical import check for Version10 T1/web deployment."""
import flask
import werkzeug
import gunicorn
import ezdxf
import pandas
import numpy
import openpyxl
import shapely
import pydantic
import yaml
import matplotlib
import PIL
import cv2

print("flask", flask.__version__)
print("werkzeug", werkzeug.__version__)
print("gunicorn", gunicorn.__version__)
print("ezdxf", ezdxf.__version__)
print("pandas", pandas.__version__)
print("numpy", numpy.__version__)
print("openpyxl", openpyxl.__version__)
print("shapely", shapely.__version__)
print("pydantic", pydantic.__version__)
print("PyYAML", yaml.__version__)
print("matplotlib", matplotlib.__version__)
print("Pillow", PIL.__version__)
print("opencv", cv2.__version__)
from wsgi import app
print("wsgi_app", type(app).__name__, getattr(app, "name", ""))
print("IMPORT_OK")
