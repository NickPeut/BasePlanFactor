from db.session import SessionLocal, engine
from db.base import Base
from db.scheme import Scheme
from db.goal import Goal

Base.metadata.create_all(bind=engine)

session = SessionLocal()
try:
    scheme = Scheme(name="Default")
    session.add(scheme)
    session.flush()

    root = Goal(name="Повысить прибыль", scheme_id=scheme.id, parent_id=None)
    session.add(root)
    session.flush()

    sales = Goal(name="Увеличить продажи", scheme_id=scheme.id, parent_id=root.id)
    costs = Goal(name="Снизить издержки", scheme_id=scheme.id, parent_id=root.id)
    session.add_all([sales, costs])
    session.flush()

    online = Goal(name="Онлайн-каналы", scheme_id=scheme.id, parent_id=sales.id)
    offline = Goal(name="Оффлайн-каналы", scheme_id=scheme.id, parent_id=sales.id)
    session.add_all([online, offline])

    session.commit()
finally:
    session.close()
