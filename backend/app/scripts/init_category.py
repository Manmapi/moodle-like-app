from app.core.db import engine
from app.models.category import Category
from sqlmodel import Session, update

from sqlalchemy.dialects.postgresql import insert

category_data = {
    "Đại sảnh": [
        "Thông báo", 
        "Gợi ý",
        "Tin tức iNet",
        "Review sản phẩm",
        "Chia sẻ kiến thức"
    ],
    "Máy tính": [
        "Tư vấn cấu hình",
        "Overcloking & Cooling & Modding",
        "AMD", 
        "Intel",
        "GPU & Màn hình",
        "Phần cứng chung",
        "Thiết bị ngoại vi & Phụ kiện & Mạng",
        "Server / NAS / Render Farm",
    ],
    "Học tập & Sự nghiệp": [
        "Tuyển dụng - Tìm việc", 
        "Ngoại ngữ", 
        "Lập trình/CNTT",
        "Kinh tế/Luật",
        "Make Money Online",
        "Tiền điện tử"
    ]
}


def main():
    for parent_category, categories in category_data.items():
        print("Processing parent category: ", parent_category)
        with Session(engine) as session:
            parent_category_obj = Category(title=parent_category, level=1, user_id=1, parent_id=1)
            session.add(parent_category_obj)
            root_level_update_q = update(Category).values(children_count=Category.children_count + 1).where(Category.id == 1)
            session.execute(root_level_update_q)
            session.commit()
            session.refresh(parent_category_obj)

            insert_data = []

            for category in categories:
                insert_data.append(dict(
                    title=category, 
                    level=2, 
                    user_id=1, 
                    parent_id=parent_category_obj.id
                ))
            q = insert(Category).values(insert_data).on_conflict_do_nothing()
            root_category_update_q = update(Category).values(children_count=Category.children_count + len(insert_data)).where(Category.id == parent_category_obj.id)
            session.execute(q)
            session.execute(root_category_update_q)
            
            session.commit()

if __name__ == "__main__":
    main()