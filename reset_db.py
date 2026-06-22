from db import engine, Base

def reset():
    print("⚠️  This will DELETE all journey data.")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.strip().lower() == 'yes':
        try:
            Base.metadata.drop_all(bind=engine)
            print("💥 All tables dropped.")
            Base.metadata.create_all(bind=engine)
            print("✅ Database rebuilt fresh.")
        except Exception as e:
            print(f"❌ Failed: {e}")
    else:
        print("🛑 Cancelled. Nothing was changed.")

if __name__ == "__main__":
    reset()