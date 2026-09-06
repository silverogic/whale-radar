import unittest
from src.schedule13_parser import Schedule13Parser
from src.models import Form4Meta

SAMPLE_13D_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13d">
  <headerData>
    <submissionType>SCHEDULE 13D</submissionType>
  </headerData>
  <formData>
    <coverPageHeader>
      <dateOfEvent>08/17/2026</dateOfEvent>
      <issuerInfo>
        <issuerCIK>0000093314</issuerCIK>
        <issuerName>VOLITIONRX LTD</issuerName>
      </issuerInfo>
    </coverPageHeader>
    <reportingPersons>
      <reportingPersonInfo>
        <reportingPersonName>Lagoda Investment Management, L.P.</reportingPersonName>
        <aggregateAmountOwned>1652005.00</aggregateAmountOwned>
        <percentOfClass>7.4</percentOfClass>
        <typeOfReportingPerson>IA</typeOfReportingPerson>
      </reportingPersonInfo>
    </reportingPersons>
  </formData>
</edgarSubmission>
"""

SAMPLE_13G_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13g">
  <headerData>
    <submissionType>SCHEDULE 13G</submissionType>
  </headerData>
  <formData>
    <coverPageHeader>
      <eventDateRequiresFilingThisStatement>08/27/2026</eventDateRequiresFilingThisStatement>
      <issuerInfo>
        <issuerCik>0001045810</issuerCik>
        <issuerName>NVIDIA CORP</issuerName>
      </issuerInfo>
    </coverPageHeader>
    <reportingPersons>
      <reportingPersonInfo>
        <reportingPersonName>BlackRock, Inc.</reportingPersonName>
        <aggregateAmountOwned>185000000.00</aggregateAmountOwned>
        <percentOfClass>7.8</percentOfClass>
        <typeOfReportingPerson>HC</typeOfReportingPerson>
      </reportingPersonInfo>
    </reportingPersons>
  </formData>
</edgarSubmission>
"""

SAMPLE_LOW_PERCENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13g">
  <headerData>
    <submissionType>SCHEDULE 13G</submissionType>
  </headerData>
  <formData>
    <coverPageHeader>
      <dateOfEvent>08/27/2026</dateOfEvent>
      <issuerInfo>
        <issuerCik>0001045810</issuerCik>
        <issuerName>NVIDIA CORP</issuerName>
      </issuerInfo>
    </coverPageHeader>
    <reportingPersons>
      <reportingPersonInfo>
        <reportingPersonName>Small Fund LLC</reportingPersonName>
        <aggregateAmountOwned>10000.00</aggregateAmountOwned>
        <percentOfClass>3.2</percentOfClass>
      </reportingPersonInfo>
    </reportingPersons>
  </formData>
</edgarSubmission>
"""

class TestSchedule13Parser(unittest.TestCase):
    def setUp(self):
        self.parser = Schedule13Parser(min_percent=5.0)
        self.dummy_meta = Form4Meta(
            accession_number="0001493152-26-041611",
            cik="0001632108",
            clean_acc_no="000149315226041611",
            filing_date="2026-09-04",
            title="SCHEDULE 13D - Lagoda Investment Management",
            index_url="https://www.sec.gov/Archives/edgar/data/1632108/000149315226041611/index.htm"
        )

    def test_parse_valid_13d(self):
        trade = self.parser.parse_and_filter(SAMPLE_13D_XML, self.dummy_meta)
        self.assertIsNotNone(trade)
        self.assertEqual(trade.category, "13D")
        self.assertEqual(trade.ticker, "VNRX")  # CIK 0000093314 -> VNRX
        self.assertEqual(trade.reporter_name, "Lagoda Investment Management, L.P.")
        self.assertEqual(trade.percent_of_class, 7.4)
        self.assertEqual(trade.total_shares, 1652005.0)
        self.assertIn("투자자문사", trade.investor_type)
        self.assertFalse(trade.is_amendment)

    def test_parse_valid_13g(self):
        meta_13g = Form4Meta(
            accession_number="0001213900-26-097798",
            cik="0002062187",
            clean_acc_no="000121390026097798",
            filing_date="2026-09-04",
            title="SCHEDULE 13G - BlackRock, Inc.",
            index_url="https://www.sec.gov/Archives/edgar/data/2062187/000121390026097798/index.htm"
        )
        trade = self.parser.parse_and_filter(SAMPLE_13G_XML, meta_13g)
        self.assertIsNotNone(trade)
        self.assertEqual(trade.category, "13G")
        self.assertEqual(trade.ticker, "NVDA")  # CIK 0001045810 -> NVDA
        self.assertEqual(trade.reporter_name, "BlackRock, Inc.")
        self.assertEqual(trade.percent_of_class, 7.8)
        self.assertIn("지주회사", trade.investor_type)

    def test_filter_out_below_five_percent(self):
        trade = self.parser.parse_and_filter(SAMPLE_LOW_PERCENT_XML, self.dummy_meta)
        self.assertIsNone(trade)

if __name__ == "__main__":
    unittest.main()
