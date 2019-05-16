from unittest import TestCase

from tests.helper import BaseTest
from py12306.app.query import *


class TestQueryTicket(BaseTest):
    task = {
        'name': 'admin',
    }
    query_dict = {
        'left_date': '2019-05-18',
        'left_station': 'BJP',
        'arrive_station': 'LZJ',
        'allow_seats': ['二等座'],
        'members': ['test']
    }
    query: QueryTicketData
    ticket_str = 'iV6uPpzX3CcwqhHe4yzrJHp9hFVCouaXtS01wlUB8f%2BuA%2BKD%2FTV5KLu37w1aKHO2zlAlwMDa%2FDYY%0A2xykUxU964zvkfI3qZZ6uGEKWi0tXCT8fhkQTVvnRI43%2FAinVozab2W1Cq%2FMzJtGBv3D1Q3CscAj%0ANA1XmfNzd6Carglhzvyyy63MkbLIRvxrngx9F01W9jhKXnQupQNTOM3Pw4UIxbesBWkmQfYNj%2Fj%2F%0A3mU33kluoI5vbGVsm115Ec%2BS29KPeaM%2B4%2F2h2UZsiCb%2F5hKfew8Hijodr2VuFftbkge1meSTRRvz%0A|预订|240000G42704|G427|BXP|LAJ|BXP|LAJ|06:21|13:44|07:23|Y|nhsXhn1BbGmb4MI%2BEto43zoslKFQlIY8c356nXAHAEk9Zb2G|20190518|3|P3|01|05|0|0|||||||||||有|无|5||O090M0|O9M|0|0|null'
    ticket: TicketData

    def setUp(self) -> None:
        super().setUp()
        self.ticket = QueryParser.parse_ticket([self.ticket_str])[0]
        self.query = QueryTicketData(self.query_dict)

    def test_get_query_api_type(self):
        res = QueryTicket().get_query_api_type()
        self.assertEqual('leftTicket/query', res)

    def test_get_ticket(self):
        res = QueryTicket().get_ticket(self.query_dict)

    def test_is_ticket_valid(self):
        res = QueryTicket().is_ticket_valid(self.ticket, self.query)
        self.assertEqual(res, True)

    def test_verify_period(self):
        self.query.left_periods = [('08:00', '16:00')]
        res = QueryTicket.verify_period('12:00', self.query.left_periods)
        self.assertEqual(res, True)
        res = QueryTicket.verify_period('16:00', self.query.left_periods)
        self.assertEqual(res, True)
        res = QueryTicket.verify_period('16:01', self.query.left_periods)
        self.assertEqual(res, False)

    def test_verify_ticket_num(self):
        self.ticket.ticket_num = 'Y'
        res = QueryTicket.verify_ticket_num(self.ticket)
        self.assertEqual(res, True)

    def test_verify_seat(self):
        self.query.allow_seats = ['硬座', '二等座']
        res = QueryTicket().verify_seat(self.ticket, self.query)
        self.assertEqual(res, True)
        self.assertEqual(self.query.available_seat.num, 30)


class TestQueryParser(TestCase):
    tickets = [
        'iV6uPpzX3CcwqhHe4yzrJHp9hFVCouaXtS01wlUB8f%2BuA%2BKD%2FTV5KLu37w1aKHO2zlAlwMDa%2FDYY%0A2xykUxU964zvkfI3qZZ6uGEKWi0tXCT8fhkQTVvnRI43%2FAinVozab2W1Cq%2FMzJtGBv3D1Q3CscAj%0ANA1XmfNzd6Carglhzvyyy63MkbLIRvxrngx9F01W9jhKXnQupQNTOM3Pw4UIxbesBWkmQfYNj%2Fj%2F%0A3mU33kluoI5vbGVsm115Ec%2BS29KPeaM%2B4%2F2h2UZsiCb%2F5hKfew8Hijodr2VuFftbkge1meSTRRvz%0A|预订|240000G42704|G427|BXP|LAJ|BXP|LAJ|06:21|13:44|07:23|Y|nhsXhn1BbGmb4MI%2BEto43zoslKFQlIY8c356nXAHAEk9Zb2G|20190518|3|P3|01|05|0|0|||||||||||有|无|5||O090M0|O9M|0|0|null',
        'UY8SmgFA1grdsKcN7%2B4133%2FSWTQqk8wVKcdLNsk6EAiuPIaE5aPPzUr9f%2FepLG0hLchNAKjlOl71%0AbMcW3HypGxckM8L3Hz1rg3ds77qPxXXDFxMITHRQfZzSoM8uqSKPdVwT4mEs6ynZ2Niw7M3iAHbq%0A0qjpuj%2FaAc5yiWsvHxAGc3UQPqchrXjcabyp9%2Bnmf7z84Ep74XirfcRmAmZopq%2B9ySctz9lnwule%0A%2FaSdcAWypluKLPobkAdSpxwndKk8bV2U%2Bq%2BbGPaNEzy2i9ixRdaBBLkg3OAqHaCBetr9gHFEiYXu%0A|预订|240000G4290C|G429|BXP|LAJ|BXP|LAJ|10:45|19:45|09:00|Y|4lti%2FihSxlRgd8xN4SFzPvGmpcT90cvJFfy4V5IGfmyCNl6r|20190518|3|P4|01|16|0|0|||||||||||有|有|5||O0M090|OM9|0|0|null',
        'VUb2s9O%2BqvddST8Tk%2BT8PzHNjzrMsp301eZv9ukz3jw55DHXLMpQ3ZK92ystqCe9atpD7DFlHiHD%0AB9q%2F4EoAaoU3OwacLHAEMtr9fX%2FYXwuCMhHmQHw%2BL8eejS9QgR5ZQM8oV6%2FeaJ5x5KqCIutwZBtz%0AgzuRZ%2FpOHSGdg03WWOXdWHVpJrBUleLGpQZ%2BQJMz0YGrl1Md%2BpNu5ypNdyKg6AyYjmZs4fRz6Slj%0AwCbQlhkclS2mvxpAE5gSJZ3nY8IjFelQTAqt6XTEHPsZ7Rd%2FNHwOM7UtlbQy7NyBCHTLgIAjuB58%0ADEpzVw%3D%3D|预订|240000T1750J|T175|BXP|XNO|BXP|LZJ|13:05|07:44|18:39|Y|g%2F3wSCFH0UvzDmFPO8NuyXGeIMI26cl93Qzex2RLyufZ8M5i2%2FvdylS8zKM%3D|20190518|3|P4|01|13|0|0||||无|||有||有|有|||||10401030|1413|0|0|null',
        'dPVMZOEQT2rtEi5BNTY2h1nNhp2H%2BA%2BKZaZINqEQ2RUbeKK%2BFeC1y%2Bm8NdO%2BlS4Ag8r6hsWfWHdL%0AX7DrJJMRMuEXnCwqcc%2Bnwd%2BfvdaeozWFuGE08OFZzJbGnnL%2F54VMSdUnapJ4jWVvsYLG2RUqopiX%0AjDavL7dBULGrfNZN4EMTBFqUz%2BzqnmDGvf3RaXr7EHrztAJSNEQc09PqlGHs65B3VaFhN%2Fa0%2BgVQ%0AXCIAP1YysdgqDXMndNNq4nkMX21Jruvi8ToQWsGnYCf%2F7OIzS5HwOu3PElDZ9bMfempLAFk%3D|预订|2400000Z550M|Z55|BXP|LZJ|BXP|LZJ|14:58|07:30|16:32|Y|nNj9EIzgMtJaVlhUo0gt3HKZi820vP3HktntoPUe%2FFW%2BDfiv|20190518|3|P4|01|06|0|0||11||有|||||有||||||604030|643|0|0|null',
        'V%2F6N%2BhZhuqxSnfkLwZHsgPQBDsGMcJkhZXyuWQLCKlzv7T%2BMvJerzW2u2TBoM8aRbqVkjywXT99K%0AdGcCUHmNOqXqngnHnvg1yj0jvsfQHPRHKIPa6hl0QeX%2BgM%2F%2Ffyj8opU919pW4YT3HViE0hQ8vNRT%0AUQOdJmbSFo1b3xI05cuzh4j21RuP9sdgaA%2BnheYMTvyMoYiEUvN1%2BClGrlrbXnhHgSWFUMxu88sG%0AQGpnqTLtVx27AAe58c9qy5oq35lOnf5OV6%2BUebB7n4YYy7ZpugZ1gyPndGGhvQdg8j58HFo%2FY%2BC1%0AzbdwhA%3D%3D|预订|2400000Z7508|Z75|BXP|LZJ|BXP|LZJ|15:57|10:30|18:33|Y|bIdN7uqCXyxKnuLinwN1naNDcYioI7Xuk535Xl1xm6Wn8CRtk2knPYx5MW4%3D|20190518|3|P4|01|07|0|0||||有|||有||有|有|||||10401030|1413|0|0|null',
        '2WQo8Fm2OT6Y016qIB5vRQNikHMVarIhB9YUu7sDFKMTC3RFxmi7Y%2BE9S%2BjdYxUoEfUiqhj%2F8ZX1%0A1GpE8Vikd5urQLbp5%2FjkES9798ohE3dQwZ0ffKHX%2FQiIl4maKmdVKebWTyV8IMgTThm5C1l%2B8csY%0ApM0kaFEsQtERyf8Mh9FH9vQDxn2Vtb%2FoOPY2UvNS%2F8Tf%2BNWni21Dh8tRZ0ZL9CBYl6%2BRbNphYSZy%0AhQASZ9fG%2BjJe96bZL%2FsuMvFa%2FTNG51k07G8mggtoqgREp0zP0cdBHjkOm%2BTmMuK7uqLS9gUodYds%0ApEj%2B%2Bg%3D%3D|预订|240000Z1510B|Z151|BXP|XNO|BXP|LZJ|16:03|11:19|19:16|Y|TM4VyMprWgU1m%2ByEJxolE3Hutch%2FGYoyOMLhudWSaubKi5OeWcwS8XZJvkU%3D|20190518|3|P2|01|09|0|0||||无|||有||有|有|||||10401030|1413|0|0|null',
        'i4IZi6FeuPVecIlQ7MMdptQ77XQ6DEH14WRtbCN1%2FJViWj7liJ3qUEJ9ml3aC9%2B8cBPbKsVHycxa%0ApoLgwMxEcxJ8LdFDeWHSJ%2FbRPyw0Ygs3tYGz%2FTYv4Ys03Oc6NGJsXlt76XQ6Lmm6fDVs%2FKnsWARg%0Ar2NxqMn0ecRGgiDAcVRF4CApE3cdE2GW0%2Blt7xcbPTDc3R2vawIAk8zKlMWKaMReXfqgeeln%2BAIV%0Aa9KSTBxgR9pC85I%2BVMJe4mYVLeUaSa%2FI7fYrXfJyVu%2BDDdiQaWEwLsTlmh7cxkGZlosHLtJh14Ym%0A6xjrqg%3D%3D|预订|2400000Z210D|Z21|BXP|LSO|BXP|LZJ|20:00|12:17|16:17|Y|et1f50q%2B5c5I%2B9WjMAG7QRRd%2F5lr5LzzS%2Bijw0HrPjMGTPoFY0BytCT68Ho%3D|20190518|3|P2|01|05|0|0||||无|||有||无|有|||||10401030|1413|0|0|null',
        'XyBvey3WmmF82TTYlMRIMGTG9tntgOjqf7d9Y7YgdZTP16T3Ts1loq5oqe9XUOrKNJxRGUmv4Q9h%0AkbnGYxvHA4LgWlDsyqO%2B%2B6SoX%2BW%2BtCH%2BC5JXvabJcaN%2BfZjQa8aBYvHHNx4li28D4tlCfrKnkB%2BU%0AzHfTSG6ekFF5K53clwbEyaljpJDdCi6uSQqMPUkslA1RQ4KAQPnXEbDbz4oC9IdjGiiTTPuC7QJU%0A0r2VW5TnKXvJr6toDWogGW8icGjeuDVcNKn%2B5OltBdNJD5bheKSE4hjzv8HauF8H%2Bb3c77jzHqSk%0ANtV%2Bgw%3D%3D|预订|250000K8880P|K885|TJP|LAJ|BJP|LZJ|23:43|05:07|29:24|Y|A1VIUe1w8dwrEhQacQ1O8SQntd7wRO0M%2Bck0TjWwuZgB%2Fi%2BVT2cxShZVqzQ%3D|20190518|3|P4|03|15|0|0||||无|||无||无|有|||||10403010|1431|1|0|null'
    ]

    def test_parse_ticket(self):
        res = QueryParser.parse_ticket(self.tickets)
        self.assertEqual(res[0].left_station, 'BXP')
        self.assertEqual(res[0].train_number, 'G427')
