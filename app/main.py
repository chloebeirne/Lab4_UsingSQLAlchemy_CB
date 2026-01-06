from fastapi import FastAPI, Depends, HTTPException, status, Response 
from sqlalchemy.orm import Session 
from sqlalchemy import select 
from sqlalchemy.exc import IntegrityError 
from sqlalchemy.orm import selectinload 
from .database import engine, SessionLocal 
from .models import Base, UserDB, CourseDB, ProjectDB 
from .schemas import (
    UserCreate, UserRead,
    CourseCreate, CourseRead,
    ProjectCreate, ProjectRead,
    ProjectReadWithOwner, ProjectCreateForUser,
    UserPut, UserPatch,
    ProjectPut, ProjectPatch
)
 
app = FastAPI() 
Base.metadata.create_all(bind=engine) 
 
def get_db(): 
    db = SessionLocal() 
    try: 
        yield db 
    finally: 
        db.close() 
 
def commit_or_rollback(db: Session, error_msg: str): 
    try: 
        db.commit() 
    except IntegrityError: 
        db.rollback() 
        raise HTTPException(status_code=409, detail=error_msg) 
 
@app.get("/health") 
def health(): 
    return {"status": "ok"} 
 
#Courses 
@app.post("/api/courses", response_model=CourseRead, status_code=201, summary="You could add details") 
def create_course(course: CourseCreate, db: Session = Depends(get_db)): 
    db_course = CourseDB(**course.model_dump()) 
    db.add(db_course) 
    commit_or_rollback(db, "Course already exists") 
    db.refresh(db_course) 
    return db_course 
 
@app.get("/api/courses", response_model=list[CourseRead]) 
def list_courses(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)): 
    stmt = select(CourseDB).order_by(CourseDB.id).limit(limit).offset(offset) 
    return db.execute(stmt).scalars().all() 
 
#Projects 
@app.post("/api/projects", response_model=ProjectRead, status_code=201) 
def create_project(project: ProjectCreate, db: Session = Depends(get_db)): 
    user = db.get(UserDB, project.owner_id) 
    if not user: 
        raise HTTPException(status_code=404, detail="User not found") 
 
    proj = ProjectDB( 
        name=project.name, 
        description=project.description, 
        owner_id=project.owner_id, 
    ) 
    db.add(proj) 
    commit_or_rollback(db, "Project creation failed") 
    db.refresh(proj) 
    return proj 
 
@app.get("/api/projects", response_model=list[ProjectRead]) 
def list_projects(db: Session = Depends(get_db)): 
    stmt = select(ProjectDB).order_by(ProjectDB.id) 
    return db.execute(stmt).scalars().all() 
 
@app.get("/api/projects/{project_id}", response_model=ProjectReadWithOwner) 
def get_project_with_owner(project_id: int, db: Session = Depends(get_db)): 
    stmt = select(ProjectDB).where(ProjectDB.id == project_id).options(selectinload(ProjectDB.owner)) 
    result = db.execute(stmt)
    rows = result.scalars().all()
    return rows
    proj = db.execute(stmt).scalar_one_or_none() 
    if not proj: 
        raise HTTPException(status_code=404, detail="Project not found") 
    return proj 
 
#Nested Routes 
@app.get("/api/users/{user_id}/projects", response_model=list[ProjectRead]) 
def get_user_projects(user_id: int, db: Session = Depends(get_db)): 
    stmt = select(ProjectDB).where(ProjectDB.owner_id == user_id) 
    #space it out for debugging 
    result = db.execute(stmt) 
    rows = result.scalars().all() 
    return rows 
    #return db.execute(stmt).scalars().all() 
 
@app.post("/api/users/{user_id}/projects", response_model=ProjectRead, status_code=201) 
def create_user_project(user_id: int, project: ProjectCreateForUser, db: Session = 
Depends(get_db)): 
    user = db.get(UserDB, user_id) 
    if not user: 
        raise HTTPException(status_code=404, detail="User not found") 
 
    proj = ProjectDB( 
        name=project.name, 
        description=project.description,   # <-- set it 
        owner_id=user_id 
    ) 
    db.add(proj) 
    commit_or_rollback(db, "Project creation failed") 
    db.refresh(proj) 
    return proj 
 
@app.get("/api/users", response_model=list[UserRead]) 
def list_users(db: Session = Depends(get_db)): 
    stmt = select(UserDB).order_by(UserDB.id) 
    #Useful for debugging 
    result = db.execute(stmt) 
    users = result.scalars().all() 
    return users 
    #return list(db.execute(stmt).scalars()) 
 
@app.get("/api/users/{user_id}", response_model=UserRead) 
def get_user(user_id: int, db: Session = Depends(get_db)): 
    user = db.get(UserDB, user_id) 
    if not user: 
        raise HTTPException(status_code=404, detail="User not found") 
    return user 
 
@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED) 
def add_user(payload: UserCreate, db: Session = Depends(get_db)): 
    user = UserDB(**payload.model_dump()) 
    db.add(user) 
    try: 
        db.commit() 
        db.refresh(user) 
    except IntegrityError: 
        db.rollback() 
        raise HTTPException(status_code=409, detail="User already exists") 
    return user 
 
# DELETE a user (triggers ORM cascade -> deletes their projects too) 
@app.delete("/api/users/{user_id}", status_code=204) 
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response: 
    user = db.get(UserDB, user_id) 
    if not user: 
        raise HTTPException(status_code=404, detail="User not found") 
    db.delete(user)          # <-- triggers cascade="all, delete-orphan" on projects 
    db.commit() 
    return Response(status_code=status.HTTP_204_NO_CONTENT) 

@app.put("/api/users/{user_id}", response_model=UserRead)
def put_user(user_id: int, user: UserPut, db: Session = Depends(get_db)):
    db_user = db.get(UserDB, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.name = user.name
    db_user.email = user.email
    db_user.age = user.age
    db_user.student_id = user.student_id

    commit_or_rollback(db, "User update failed")
    db.refresh(db_user)
    return db_user


@app.patch("/api/users/{user_id}", response_model=UserRead)
def patch_user(user_id: int, user: UserPatch, db: Session = Depends(get_db)):
    db_user = db.get(UserDB, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    data = user.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(db_user, k, v)

    commit_or_rollback(db, "User update failed")
    db.refresh(db_user)
    return db_user


@app.put("/api/projects/{project_id}", response_model=ProjectRead)
def put_project(project_id: int, project: ProjectPut, db: Session = Depends(get_db)):
    db_proj = db.get(ProjectDB, project_id)
    if not db_proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # validate owner exists
    owner = db.get(UserDB, project.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")

    db_proj.name = project.name
    db_proj.description = project.description
    db_proj.owner_id = project.owner_id

    commit_or_rollback(db, "Project update failed")
    db.refresh(db_proj)
    return db_proj


@app.patch("/api/projects/{project_id}", response_model=ProjectRead)
def patch_project(project_id: int, project: ProjectPatch, db: Session = Depends(get_db)):
    db_proj = db.get(ProjectDB, project_id)
    if not db_proj:
        raise HTTPException(status_code=404, detail="Project not found")

    data = project.model_dump(exclude_unset=True)

    # if owner_id is being updated, validate it
    if "owner_id" in data:
        owner = db.get(UserDB, data["owner_id"])
        if not owner:
            raise HTTPException(status_code=404, detail="User not found")

    for k, v in data.items():
        setattr(db_proj, k, v)

    commit_or_rollback(db, "Project update failed")
    db.refresh(db_proj)
    return db_proj
