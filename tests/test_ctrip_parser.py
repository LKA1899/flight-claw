import unittest

from app.parsers.ctrip_parser import parse_ctrip_html


class CtripParserTest(unittest.TestCase):
    def test_parses_only_flight_rows_from_ctrip_result_text(self) -> None:
        html = """
        <html><body>
        更多日期 09-22 周二 ¥2781 低 09-23 周三 ¥3050
        更多排序 低价提醒
        Centrum Air 2个航司 2程航班 09:30 大兴国际机场
        转1次 转 塔什干9h15m 00:25 +1天 第比利斯国际机场
        18小时55分 航班详情 ¥3485起 含税价 订票
        阿斯塔纳航空 KC228 空客321(中) KC119 空客321(中)
        01:30 首都国际机场 T2 转1次 转 阿斯塔纳9h20m
        16:35 第比利斯国际机场 19小时5分 航班详情 ¥4020起 含税价 订票
        中国国航 CA1973 波音737MAX8(中) CA781 波音737MAX8(中)
        20:45 首都国际机场 T3 转1次 转 乌鲁木齐18h
        21:05 +1天 第比利斯国际机场 1天4小时20分 航班详情 ¥4130起 含税价 订票
        在线客服 旅游资讯 Copyright
        </body></html>
        """

        items = parse_ctrip_html(html)

        self.assertEqual([item.price for item in items], [3485.0, 4020.0, 4130.0])
        self.assertEqual(items[0].airline, "Centrum Air")
        self.assertIsNone(items[0].flight_no)
        self.assertEqual(items[0].depart_time, "09:30")
        self.assertEqual(items[0].arrive_time, "00:25")
        self.assertEqual(items[0].duration_minutes, 18 * 60 + 55)
        self.assertEqual(items[0].transfer_city, "塔什干")
        self.assertEqual(items[1].flight_no, "KC228/KC119")
        self.assertEqual(items[2].flight_no, "CA1973/CA781")


if __name__ == "__main__":
    unittest.main()
