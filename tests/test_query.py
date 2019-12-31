import copy
from app.models import QueryJob, Ticket
from app.query import QueryTicket
from tests import BaseTest, async_test


class QueryTicketTests(BaseTest):

    @async_test
    async def setUp(self) -> None:
        super().setUp()
        self.query = await QueryJob.first()
        self.query_ticket = QueryTicket(self.query)
        # init query
        self.query.left_date = self.query.left_dates[0]
        self.query.left_station, self.query.arrive_station = self.query.stations[0]

    @async_test
    async def test_get_query_api_type(self):
        ret = await self.query_ticket.get_query_api_type()
        self.assertIn(ret, ['leftTicket/query', 'leftTicket/queryO', 'leftTicket/queryZ'])

    @async_test
    async def test_query_tickets(self):
        ret = await self.query_ticket.query_tickets()

    @async_test
    async def test_get_available_tickets(self):
        ret = await self.query_ticket.get_available_tickets(self.query)
        for ticket in ret[0]:
            self.assertIsInstance(ticket, Ticket)
        self.assertTrue(ret[1] >= 0)

    @async_test
    async def test_get_tickets_from_query(self):
        ret = await self.query_ticket.get_tickets_from_query(self.query)
        for ticket in ret:
            self.assertIsInstance(ticket, Ticket)

    @async_test
    async def test_is_ticket_valid(self):
        tickets = await self.query_ticket.get_tickets_from_query(self.query)
        for ticket in tickets:
            ret = self.query_ticket.is_ticket_valid(ticket)
            self.assertIsInstance(ret, bool)

    def test_verify_period(self):
        query = copy.deepcopy(self.query)
        query.left_periods = ['08:00', '16:00']
        ret = QueryTicket.verify_period('12:00', query.left_periods)
        self.assertEqual(ret, True)
        ret = QueryTicket.verify_period('16:00', query.left_periods)
        self.assertEqual(ret, True)
        ret = QueryTicket.verify_period('16:01', query.left_periods)
        self.assertEqual(ret, False)

    def test_verify_ticket_num(self):
        ticket = Ticket()
        ticket.ticket_num = 'Y'
        ticket.order_text = '预订'
        ret = self.query_ticket.verify_ticket_num(ticket)
        self.assertEqual(ret, True)

    def test_verify_seat(self):
        query = copy.deepcopy(self.query)
        query.allow_seats = ['硬座', '二等座']  # 29, 30
        ticket = Ticket()
        ticket.raw = {29: '*', 30: '有'}
        ret = self.query_ticket.verify_seat(ticket, query)
        self.assertEqual(ret, True)
        self.assertEqual(ticket.available_seat.get('id'), 30)

    def test_verify_train_number(self):
        query = copy.deepcopy(self.query)
        query.allow_train_numbers = ['G427', 'G429', 'T175']
        ticket = Ticket()
        ticket.train_number = 'G427'
        ret = self.query_ticket.verify_train_number(ticket, query)
        self.assertEqual(True, ret)
        ticket.train_number = 'B427'
        ret = self.query_ticket.verify_train_number(ticket, query)
        self.assertEqual(False, ret)

    def test_verify_member_count(self):
        query = copy.deepcopy(self.query)
        query.member_num = 5
        ticket = Ticket()
        ticket.available_seat = {'name': '二等座', 'id': 30, 'raw': '3', 'order_id': 'O'}
        ret = self.query_ticket.verify_member_count(ticket, query)
        self.assertEqual(False, ret)
        query.less_member = True
        ret = self.query_ticket.verify_member_count(ticket, query)
        self.assertEqual(True, ret)

    def test_get_query_interval(self):
        ret = self.query_ticket.get_query_interval()
        self.assertTrue(ret >= 0)

    def test_action(self):
        self.assertEqual(self.query_ticket.is_runable, True)
        self.query_ticket.stop()
        self.assertEqual(self.query_ticket.is_runable, False)
        self.assertEqual(self.query_ticket.is_stoped, True)
