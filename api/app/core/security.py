import bcrypt


def hash_password(plain: str) -> str:
    # gensalt stvara novi salt i upisuje ga u rezultat, uz algoritam i faktor rada
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    # checkpw iz zapisa iscita salt i faktor rada, ponovi izracun i usporedi
    # u stalnom vremenu, pa iz trajanja usporedbe nista ne slijedi
    return bcrypt.checkpw(plain.encode(), hashed.encode())
