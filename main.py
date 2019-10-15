import psycopg2.errors
import psycopg2.extensions

USER = 'test'
DATABASE = 'test'


def submit(make_connection, user):
    with make_connection() as connection:
        # 先检查有没有人已经拿到第一道题的全场一血
        with connection.cursor() as cursor:
            cursor.execute(
                'select * from flag_first'
                '    where "challenge" = 1 and "group" IS NULL',
            )
            data = cursor.fetchall()
        yield
        # 如果有超过一个人拿到，说明出现了数据库不一致
        assert len(data) <= 1, 'Serialization anomaly!'
        try:
            if data:
                # 如果有人拿到了，则自己不是一血
                print(f'user {user}: not first')
            else:
                # 自己拿到了一血，写入数据库
                with connection.cursor() as cursor:
                    cursor.execute(
                        'insert into flag_first values(1, NULL, %s)',
                        (user,)
                    )
                print(f'user {user}: first')
            connection.commit()
        except psycopg2.errors.SerializationFailure:
            # 本次请求出错
            print(f'user {user}: error')
    yield


def main(isolation_level):
    def make_connection(isolation_level=isolation_level):
        connection = psycopg2.connect(user=USER, database=DATABASE)
        connection.autocommit = False
        connection.isolation_level = isolation_level
        return connection

    with psycopg2.connect(user=USER, database=DATABASE) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'create table if not exists flag_first('
                '    "challenge" int not null,'
                '    "group"     text,'
                '    "user"      int not null,'
                '    unique("challenge", "group"))'
            )
        with connection.cursor() as cursor:
            cursor.execute('delete from flag_first')
    # 三个用户来操作
    a = submit(make_connection, user=1)
    b = submit(make_connection, user=2)
    c = submit(make_connection, user=3)
    # 前两个用户几乎同时提交正确答案
    next(a)
    next(b)
    next(a)
    next(b)
    # 第三个用户之后提交正确答案
    next(c)
    next(c)


if __name__ == '__main__':
    print('serializable isolation level:')
    main(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
    print('repeatable read (a.k.a. snapshot) isolation level:')
    main(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
