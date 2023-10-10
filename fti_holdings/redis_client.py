import redis
from time import sleep
from toolkit.logger import Logger

r = redis.Redis(host='localhost', port=6379)
logging = Logger(30, "redis.log")


class RedisClient:

    def authenticate(self):
        try:
            response = r.ping()
            if response:
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Error: {str(e)}")

    def get_one(self, itemid: int) -> None:
        error_count = 0
        retry = 5
        attempt = 0
        while True:
            try:
                quote = r.hget(itemid, "last_price")
                if not quote:
                    r.hset(itemid, "last_price",  -1)
                    r.expire(itemid, retry)
                    continue
                elif float(quote.decode('utf-8')) < 0:
                    if attempt <= retry:
                        logging.debug(
                            f"waiting for server {itemid} "
                            f" {float(quote.decode('utf-8'))} "
                        )
                        attempt += 1
                        sleep(attempt * 0.1)
                        continue
                    else:
                        logging.debug(f"given up {quote}")
                        quote = None
                        break
                else:
                    quote = float(quote.decode('utf-8'))
                    break
            except ValueError as v:
                logging.debug(f"value error {v}")
                quote = None
                break
            except Exception as e:
                error_count += 1
                print(e)
                logging.warning(
                    "Error #%d: %s; retrying",
                    error_count, itemid
                )
                quote = None
                break
        return quote

    def ltp(self, lst_exchsym):
        dct = {}
        new_lst = []
        if isinstance(lst_exchsym, list):
            for lst in lst_exchsym:
                quote = self.get_one(lst)
                new_lst.append(quote)
        dct = {lst_exchsym[i]: new_lst[i] for i in range(len(new_lst))}
        dct = {k: v for k, v in dct.items() if v is not None}
        return dct


if __name__ == "__main__":
    cl = RedisClient()
    lst = ['NSE:CANBK', 'NSE:HINDALCO', 'NSE:HDFCBANK']
    resp = cl.ltp(lst)
    print(resp)
