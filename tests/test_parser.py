import unittest
from src.parser import Form4Parser
from src.models import Form4Meta

SAMPLE_VALID_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <periodOfReport>2026-09-04</periodOfReport>
    <issuer>
        <issuerTradingSymbol>NVEC</issuerTradingSymbol>
        <issuerName>NVE CORP /NEW</issuerName>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerName>Baker Daniel A</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isOfficer>1</isOfficer>
            <isDirector>1</isDirector>
            <isTenPercentOwner>0</isTenPercentOwner>
            <officerTitle>President and CEO</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-09-04</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1000</value></transactionShares>
                <transactionPricePerShare><value>80.00</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>143000</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-09-04</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1500</value></transactionShares>
                <transactionPricePerShare><value>82.00</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>144500</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

SAMPLE_OPTION_EXERCISE_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer><issuerTradingSymbol>TEST</issuerTradingSymbol></issuer>
    <reportingOwner>
        <reportingOwnerId><rptOwnerName>John Doe</rptOwnerName></reportingOwnerId>
        <reportingOwnerRelationship>
            <isOfficer>1</isOfficer>
            <officerTitle>CFO</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionCoding><transactionCode>M</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>10000</value></transactionShares>
                <transactionPricePerShare><value>15.00</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

SAMPLE_SMALL_VALUE_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer><issuerTradingSymbol>TEST</issuerTradingSymbol></issuer>
    <reportingOwner>
        <reportingOwnerId><rptOwnerName>Jane Smith</rptOwnerName></reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>100</value></transactionShares>
                <transactionPricePerShare><value>50.00</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

SAMPLE_VALID_SELL_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <periodOfReport>2026-09-04</periodOfReport>
    <issuer>
        <issuerTradingSymbol>TECH</issuerTradingSymbol>
        <issuerName>BIG TECH INC</issuerName>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerName>Smith John</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isOfficer>1</isOfficer>
            <officerTitle>Chief Financial Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-09-04</value></transactionDate>
            <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>5000</value></transactionShares>
                <transactionPricePerShare><value>120.00</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>20000</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

class TestForm4Parser(unittest.TestCase):
    def setUp(self):
        self.parser = Form4Parser(min_purchase_value=100000.0)
        self.dummy_meta = Form4Meta(
            accession_number="0001234567-26-000001",
            cik="0001234567",
            clean_acc_no="000123456726000001",
            filing_date="2026-09-04",
            title="4 - NVE CORP /NEW",
            index_url="https://www.sec.gov/Archives/edgar/data/1234567/000123456726000001/index.htm"
        )

    def test_valid_insider_buying(self):
        # 1000 * 80 ($80k) + 1500 * 82 ($123k) = $203,000 (>= $100k)
        trade = self.parser.parse_and_filter(SAMPLE_VALID_XML, self.dummy_meta)
        self.assertIsNotNone(trade)
        self.assertEqual(trade.ticker, "NVEC")
        self.assertEqual(trade.trade_type, "BUY")
        self.assertEqual(trade.reporter_name, "Baker Daniel A")
        self.assertEqual(trade.role_title, "President and CEO")
        self.assertTrue(trade.is_officer)
        self.assertTrue(trade.is_director)
        self.assertEqual(trade.total_shares, 2500)
        self.assertEqual(trade.total_value_usd, 203000.0)
        self.assertAlmostEqual(trade.avg_price, 81.20, places=2)
        self.assertEqual(trade.shares_owned_after, 144500)
        self.assertEqual(len(trade.items), 2)

    def test_valid_insider_selling(self):
        # 5000 * 120 = $600,000 (>= $100k), Code S, AcquiredDisposed D
        trade = self.parser.parse_and_filter(SAMPLE_VALID_SELL_XML, self.dummy_meta)
        self.assertIsNotNone(trade)
        self.assertEqual(trade.ticker, "TECH")
        self.assertEqual(trade.trade_type, "SELL")
        self.assertEqual(trade.reporter_name, "Smith John")
        self.assertEqual(trade.role_title, "Chief Financial Officer")
        self.assertEqual(trade.total_shares, 5000)
        self.assertEqual(trade.total_value_usd, 600000.0)
        self.assertEqual(trade.shares_owned_after, 20000)
        # prior shares = 20000 + 5000 = 25000 -> - (5000/25000)*100 = -20%
        self.assertAlmostEqual(trade.pct_increase, -20.0, places=1)

    def test_filter_out_option_exercise(self):
        trade = self.parser.parse_and_filter(SAMPLE_OPTION_EXERCISE_XML, self.dummy_meta)
        self.assertIsNone(trade)

    def test_filter_out_small_purchase(self):
        trade = self.parser.parse_and_filter(SAMPLE_SMALL_VALUE_XML, self.dummy_meta)
        self.assertIsNone(trade)

if __name__ == "__main__":
    unittest.main()
