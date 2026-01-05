from db.session import SessionLocal, engine
from db.goal import Base, Goal

Base.metadata.create_all(bind=engine)

session = SessionLocal()

root = Goal(name="Повысить прибыль")

sales = Goal(name="Увеличить продажи")
costs = Goal(name="Снизить издержки")

session.add(root)
session.flush()  # получаем root.id

sales.parent_id = root.id
costs.parent_id = root.id

session.add_all([sales, costs])
session.flush()  # получаем sales.id, costs.id

online = Goal(name="Онлайн-каналы", parent_id=sales.id)
offline = Goal(name="Оффлайн-каналы", parent_id=sales.id)

session.add_all([online, offline])
session.commit()
session.close()
