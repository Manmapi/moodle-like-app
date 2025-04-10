from app.core.db import engine
from app.models.thread import Thread
from sqlmodel import Session, update

from sqlalchemy.dialects.postgresql import insert

thread_data = {
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
    for parent_thread, threads in thread_data.items():
        print("Processing parent thread: ", parent_thread)
        with Session(engine) as session:
            parent_thread_obj = Thread(title=parent_thread, level=1, user_id=1, parent_id=1)
            session.add(parent_thread_obj)
            root_level_update_q = update(Thread).values(children_count=Thread.children_count + 1).where(Thread.id == 1)
            session.execute(root_level_update_q)
            session.commit()
            session.refresh(parent_thread_obj)

            insert_data = []

            for thread in threads:
                insert_data.append(dict(
                    title=thread, 
                    level=2, 
                    user_id=1, 
                    parent_id=parent_thread_obj.id
                ))
            q = insert(Thread).values(insert_data).on_conflict_do_nothing()
            root_thread_update_q = update(Thread).values(children_count=Thread.children_count + len(insert_data)).where(Thread.id == parent_thread_obj.id)
            session.execute(q)
            session.execute(root_thread_update_q)
            
            session.commit()

if __name__ == "__main__":
    main()