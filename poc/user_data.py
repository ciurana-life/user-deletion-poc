from sqlalchemy import event
from sqlalchemy.orm import Mapper


@event.listens_for(Mapper, "after_mapper_constructed")
def cehck_user_data(mapper, cls):
    print(cls.__name__, mapper.local_table.name)
    breakpoint()
    table = mapper.local_table
    if table.name != "thumbnail":
        return
    breakpoint()
