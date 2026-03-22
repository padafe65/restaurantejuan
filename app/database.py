from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración para tu MariaDB/MySQL en XAMPP
# Formato: mysql+pymysql://usuario:contraseña@servidor/nombre_db
# En XAMPP el usuario por defecto es 'root' y no tiene contraseña.
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root@localhost/restaurantjuan_db"

# El 'engine' es el encargado de la conexión física
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# La 'SessionLocal' es la que usaremos para hacer consultas (como el EntityManager en NestJS)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Esta es la clase base de la que heredarán todos nuestros modelos
Base = declarative_base()

# Esta función es un "Generador" que abrirá y cerrará la conexión automáticamente
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()