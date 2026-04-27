try:
    import uvicorn
    print("uvicorn version:", uvicorn.__version__)
except ImportError as e:
    print("uvicorn not installed:", e)
