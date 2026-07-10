<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [  
	<!ENTITY nbsp "&#160;">
]>

<xsl:stylesheet version="1.0" xmlns:tbs="urn:kr:or:kec:standard:Tax:ReusableAggregateBusinessInformationEntitySchemaModule:1:0"  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">


<xsl:output method="html" indent="yes" doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd" />

 
<!-- 웹서버상에서 설정하는 출력 포맷 파라메너값 추출 -->
<xsl:param name="WebColor"/>
<xsl:param name="WebFormat"/>
<xsl:param name="seal"/>
<xsl:param name="statusInfo"/>
<xsl:param name="DocSignYN"/>
<xsl:param name="ShowUser"/>


<!--이것은...웹이나 Agnet에서 받아야할듯하다-->
<xsl:param name="AgentColor"/>
<xsl:param name="AgentFormat"/>

<xsl:decimal-format name="staff" digit="D" NaN="" />
<xsl:template match="/">

<!-- 현금, 수표, 어음, 외상미수금 금액 Setting -->
<xsl:variable name="p_TotalAmount"    select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedMonetarySummation/tbs:GrandTotalAmount"/> 
<xsl:variable name="p_Test"           select="//tbs:ExchagnedDocument/tbs:ID"/>

<!-- 수정사유코드 -->
<xsl:variable name="p_ChgCode"        select="//tbs:TaxInvoiceDocument/tbs:AmendmentStatusCode"/>

<!-- 승인번호 -->
<xsl:variable name="p_IssueCode"        select="//tbs:TaxInvoiceDocument/tbs:IssueID"/>

<!-- 결제방법코드 V3버전도 4개인지 알아보기-->
<xsl:variable name="p_PaymentMethod1" select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[1]/tbs:TypeCode"/>
<xsl:variable name="p_PaymentMethod2" select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[2]/tbs:TypeCode"/>
<xsl:variable name="p_PaymentMethod3" select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[3]/tbs:TypeCode"/>
<xsl:variable name="p_PaymentMethod4" select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[4]/tbs:TypeCode"/>

<xsl:variable name="p_Amount1"        select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[1]/tbs:PaidAmount"/>
<xsl:variable name="p_Amount2"        select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[2]/tbs:PaidAmount"/>
<xsl:variable name="p_Amount3"        select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[3]/tbs:PaidAmount"/>
<xsl:variable name="p_Amount4" 			  select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedPaymentMeans[4]/tbs:PaidAmount"/>

<!-- 사업자 번호 세팅 -->
<xsl:variable name="p_SuppBizregno"   select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:ID"/>  
<xsl:variable name="p_DmndBizregno"   select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:ID"/>  
<xsl:variable name="p_BrokerBizregno" select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:ID"/>    
<xsl:variable name="p_BrokerCoName"   select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:NameText"/> 

<!-- 전화번호 세팅 -->
<xsl:variable name="p_DmndTel" 			  select="//tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:TelephoneCommunication"/> 
<xsl:variable name="p_DmndTel2"       select="//tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:TelephoneCommunication"/> 

<!-- 공급받는자 담당자 정보(이름) -->
<xsl:variable name="p_DmndName2" 	    select="//tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:PersonNameText"/> 
<xsl:variable name="p_Remarks3" 	    select="//tbs:TaxInvoiceDocument/tbs:DescriptionText[3]"/>

<!-- 공급받는자2 이메일 추가 -->
<xsl:variable name="p_DmndEmail2" 	    select="//tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:URICommunication"/> 

<!-- 금액 세팅 -->
<!-- total공급가액-->
<xsl:variable name="p_ChargeAmount"   select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedMonetarySummation/tbs:ChargeTotalAmount"/>  

<!-- total세액-->
<xsl:variable name="p_TotalTax"       select="//tbs:TaxInvoiceTradeSettlement/tbs:SpecifiedMonetarySummation/tbs:TaxTotalAmount"/>         

<!-- 개인세금계산서 포맷 여부 (XSL에서 처리)-->
<xsl:variable name="Dmnd_Identifier"  select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:ID"/>
<xsl:variable name="Personal_YN">
  <xsl:choose>
    <xsl:when test="string-length($Dmnd_Identifier) = 13">Y</xsl:when>
    <xsl:otherwise>N</xsl:otherwise>
  </xsl:choose>
</xsl:variable>

<!-- 상품목록 구성(4개 맞추기 위함) (Javascript에서 처리)-->
<xsl:variable name="ItemLine">
  <xsl:value-of select ="count(//tbs:TaxInvoiceTradeLineItem)"/>
</xsl:variable>


<!-- 문서 상태 표시 -->							
<xsl:variable name="url_stateImg" select="$statusInfo"/>


<!-- 출력 칼라(매입/매출) 지정(웹에서 지정이 우선, 웹 지정이 없을시 XML문서안의 값을 지정) -->
<xsl:variable name="pColor">
  <xsl:choose>
    <xsl:when test="string-length($WebColor) > 1">
        <xsl:value-of select ="$WebColor"/>
    </xsl:when>
    <xsl:otherwise>
        <xsl:value-of select ="$AgentColor"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:variable>

<!-- 웹이나 Agent에서 받아온 pColor 값이 red면 suRed로 바꿔준다. 디자이너의 css class 값이 빨강은 suRed 로 되어있어서.....  -->
<xsl:variable name="newColor">
  <xsl:choose>
    <xsl:when test="$pColor = 'blue'"></xsl:when>
    <xsl:otherwise>suRed</xsl:otherwise>
  </xsl:choose>
</xsl:variable>


<!-- 지정된 $pColor 값에 맞춰 출력문서 칼라 지정  -->
<xsl:variable name="vColor">
  <xsl:choose>
    <xsl:when test="$pColor = 'blue'">#125ec4</xsl:when>
    <xsl:otherwise>#cd3b7c</xsl:otherwise>
  </xsl:choose>
</xsl:variable>



<xsl:variable name="bg01">
  <xsl:choose>
    <xsl:when test="$pColor = 'blue'">#f2f6fa</xsl:when>
    <xsl:otherwise>#fff6f9</xsl:otherwise>
  </xsl:choose>
</xsl:variable>

<xsl:variable name="bg02">
  <xsl:choose>
    <xsl:when test="$pColor = 'blue'">#c6d4e4</xsl:when>
    <xsl:otherwise>#eac5d5</xsl:otherwise>
  </xsl:choose>
</xsl:variable>

<!-- XML 문서안의 문서종류 가져오기 -->
<xsl:variable name="oFormat">
  <xsl:value-of select ="//tbs:TaxInvoiceDocument/tbs:TypeCode"/>
</xsl:variable>


<!-- 출력 포맷 지정(미지정시 'Normal 포맷으로 지정되어 출력) -->
<!-- 우선순위
     1. web format
     2. Show format
     3. 문서의 TypeCode
     4. default Normal    -->

<xsl:variable name="pFormat">
  <xsl:choose>
    <xsl:when test="string-length($WebFormat) > 1">
          <xsl:if test="string-length($p_BrokerBizregno) > 1">
              <xsl:value-of select ="$WebFormat"/>
          </xsl:if>
      </xsl:when>

    <xsl:when test="string-length($AgentFormat) > 1">
        <xsl:if test="string-length($p_BrokerBizregno) > 1">
            <xsl:value-of select ="$AgentFormat"/>
        </xsl:if>
    </xsl:when>

    <xsl:when test="string-length($p_BrokerBizregno) > 1">Broker</xsl:when>

    <xsl:otherwise>Normal</xsl:otherwise>
  </xsl:choose>
</xsl:variable>


<link rel="stylesheet" type="text/css" href="http://www.trusbill.or.kr/common/css/common.css" />
<link rel="stylesheet" type="text/css" href="http://www.trusbill.or.kr/common/css/contents.css" />
<link rel="stylesheet" type="text/css" href="http://www.trusbill.or.kr/common/css/tax.css" />
<!--[if IE 7]><link rel="stylesheet" type="text/css" href="http://www.trusbill.or.kr/common/css/ie7.css"><![endif]-->


<!-- 개인용/일반 세금계산서 포맷 값 확인용 -->
<script type= "text/javascript">

  var WebColor         = '<xsl:value-of select ="$WebColor"/>' ;
  var v_Test           = '<xsl:value-of select ="$p_Test"/>' ;
  var v_TotalAmount    = '<xsl:value-of select ="$p_TotalAmount"/>' ;
  var Personal_YN      = '<xsl:value-of select ="$Personal_YN"/>' ;
  var ItemLine         = '<xsl:value-of select ="$ItemLine"/>' ;                  // 상품목록 출력 줄수
  var pColor           = '<xsl:value-of select ="$pColor"/>' ;
  var vColor           = '<xsl:value-of select ="$vColor"/>' ;
  var newColor         = '<xsl:value-of select ="$newColor"/>' ;
  
  var pFormat          = '<xsl:value-of select ="$pFormat"/>' ;
  var pSignYN          = '<xsl:value-of select ="$DocSignYN"/>' ;
  var v_ShowUser       = '<xsl:value-of select ="$ShowUser"/>' ;
  var v_number         = '<xsl:value-of select ="$oFormat"/>' ;
  var v_ChgCode        = '<xsl:value-of select ="$p_ChgCode"/>' ;
  var v_IssueCode      = '<xsl:value-of select ="$p_IssueCode"/>' ;
  var dockind          = v_number.substring(0,2)
  var v_Amount1        = '<xsl:value-of select ="$p_Amount1"/>' ;
  var v_Amount2        = '<xsl:value-of select ="$p_Amount2"/>' ;
  var v_Amount3        = '<xsl:value-of select ="$p_Amount3"/>' ;
  var v_Amount4        = '<xsl:value-of select ="$p_Amount4"/>' ;
  var v_Method1        = '<xsl:value-of select ="$p_PaymentMethod1"/>' ;
  var v_Method2        = '<xsl:value-of select ="$p_PaymentMethod2"/>' ;
  var v_Method3        = '<xsl:value-of select ="$p_PaymentMethod3"/>' ;
  var v_Method4        = '<xsl:value-of select ="$p_PaymentMethod4"/>' ;
  var v_SuppBizregno   = '<xsl:value-of select ="$p_SuppBizregno"/>' ;
  var v_DmndBizregno   = '<xsl:value-of select ="$p_DmndBizregno"/>' ;
  var v_BrokerBizregno = '<xsl:value-of select ="$p_BrokerBizregno"/>' ;
  var v_BrokerCoName   = '<xsl:value-of select ="$p_BrokerCoName"/>' ;
  var v_ChargeAmount   = '<xsl:value-of select ="$p_ChargeAmount"/>' ;
  var v_TotalTax       = '<xsl:value-of select ="$p_TotalTax"/>' ;
  var v_DmndTel        = '<xsl:value-of select ="$p_DmndTel"/>' ;
  var v_DmndTel2       = '<xsl:value-of select ="$p_DmndTel2"/>' ;
  var p_DmndName2      = '<xsl:value-of select ="$p_DmndName2"/>' ;
  var v_Remarks3       = '<xsl:value-of select ="$p_Remarks3"/>';
  var p_DmndEmail2 	   = '<xsl:value-of select ="$p_DmndEmail2"/>' ;
  var seal       = '<xsl:value-of select ="$seal"/>';
  
  var BackImg1         = '../../images/documents//state_T0600.png' ;
  var v_url_stateImg   = '<xsl:value-of select ="$url_stateImg"/>';
  var ImgName 		   = v_url_stateImg.substring(v_url_stateImg.length-9);



function BackPng() {
	if(ImgName=='T0100.png'){
		document.write('<img src="/images/documents/state_T0100.png" alt="현재 세금계산서는 발급진행 중입니다." />');
	}else if(ImgName=='T0300.png' || ImgName=='T0310.png'){
		document.write('<img src="/images/documents/state_T0300.png" alt="현재 세금계산서는 발급대기 중입니다." />');
	}else if(ImgName=='T0303.png'){
		document.write('<img src="/images/documents/state_T0303.png" alt="현재 세금계산서는 관리자 서명요청 중입니다." />');
	}else if(ImgName=='T0400.png' || ImgName=='T0401.png'){
		document.write('<img src="/images/documents/state_T0400.png" alt="현재 세금계산서는 미승인 상태입니다." />');
	}else if(ImgName=='T0501.png'){
		document.write('<img src="/images/documents/state_T0501.png" alt="현재 세금계산서는 수신거부 상태입니다." />');
	}else if(ImgName=='T0502.png'){
		document.write('<img src="/images/documents/state_T0502.png" alt="현재 세금계산서는 발급거부 상태입니다." />');
	}else if(ImgName=='T0600.png'){
		document.write('<img src="/images/documents/state_T0600.png" alt="현재 세금계산서는 발급취소 상태입니다." />');
	}else if(ImgName=='T0701.png'){
		document.write('<img src="/images/documents/state_T0701.png" alt="현재 세금계산서는 공급자 취소요청 중입니다." />');
	}else if(ImgName=='T0702.png'){
		document.write('<img src="/images/documents/state_T0702.png" alt="현재 세금계산서는 공급받는자 취소요청 중입니다." />');
	}
}

  //////////////////////////////////
  // 문자열 공백제거하기
  //////////////////////////////////
  function trim(str) {
      str = str.replace(/^\s*/, "").replace(/\s*$/, "");
      return str;
  }

  //////////////////////////////////
  // 텍스트 출력(없을시 공백)
  //////////////////////////////////
  function prn_txt(t) {
    if(trim(t).length == 0){
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    } else {
      document.write(t);
    }
  }

  //////////////////////////////////
  // 금액 부문 출력(콤마 출력)
  //////////////////////////////////
  function comma_num(n) {
    var reg = /(^[+-]?\d+)(\d{3})/;      //정규식
    n += '';
    if(n == null) return ' ';
    while(reg.test(n))
      n = n.replace(reg, '$1' + ',' + '$2');
    return n;
  }

  //////////////////////////////////
  // 콤마 출력(없을시 공백)
  //////////////////////////////////
  function prn_comm(t) {
    if(trim(t).length == 0){
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    } else {
      document.write(comma_num(t));
    }
  }

  ///////////////////////////////////////////
  // 현금, 수표, 어음, 외상미수금 부문 출력
  ///////////////////////////////////////////
  function PaymentMethodPrint() {
    var v_cash = '';
    var v_check = '';
    var v_bill = '';
    var v_outstand = '';

    if(v_Method1 == '10') {          // 현금
      v_cash = v_Amount1 ;
    } else if (v_Method1 == '20') {  // 수표
      v_check = v_Amount1 ;
    } else if (v_Method1 == '30') { // 어음
      v_bill = v_Amount1 ;
    } else if (v_Method1 == '40') {  // 외상미수금
      v_outstand = v_Amount1 ;
    }

    if(v_Method2 == '10') {          // 현금
      v_cash = v_Amount2 ;
    } else if (v_Method2 == '20') {  // 수표
      v_check = v_Amount2 ;
    } else if (v_Method2 == '30') { // 어음
      v_bill = v_Amount2 ;
    } else if (v_Method2 == '40') {  // 외상미수금
      v_outstand = v_Amount2 ;
    }

    if(v_Method3 == '10') {          // 현금
      v_cash = v_Amount3 ;
    } else if (v_Method3 == '20') {  // 수표
      v_check = v_Amount3 ;
    } else if (v_Method3 == '30') {  // 어음
      v_bill = v_Amount3 ;
    } else if (v_Method3 == '40') {  // 외상미수금
      v_outstand = v_Amount3 ;
    }

    if(v_Method4 == '10') {          // 현금
      v_cash = v_Amount4 ;
    } else if (v_Method4 == '20') {  // 수표
      v_check = v_Amount4 ;
    } else if (v_Method4 == '30') { // 어음
      v_bill = v_Amount4 ;
    } else if (v_Method4 == '40') {  // 외상미수금
      v_outstand = v_Amount4 ;
    }

    document.write('<xsl:text disable-output-escaping="yes"><![CDATA[');
    
    document.write('<td class="tar">&nbsp;<strong>'+ comma_num(v_TotalAmount) +'</strong>&nbsp;</td>');
    document.write('<td class="tar">&nbsp;<strong>'+ comma_num(v_cash) +'</strong>&nbsp;</td>');
    document.write('<td class="tar">&nbsp;<strong>'+ comma_num(v_check) +'</strong>&nbsp;</td>');
    document.write('<td class="tar">&nbsp;<strong>'+ comma_num(v_bill) +'</strong>&nbsp;</td>');
    document.write('<td class="tar">&nbsp;<strong>'+ comma_num(v_outstand) +'</strong>&nbsp;</td>');
    
    document.write(']]></xsl:text>');
  }

  //////////////////////////////////
  //  상품목록 출력
  //////////////////////////////////
  function BlankItemListPrint(BlankLine) {
    var i = 0 ;

    if(BlankLine.substring(0, 1) != '-') {
      do {
        if(BlankLine == 0) {break;}
        i++;
        document.write('<xsl:text disable-output-escaping="yes"><![CDATA[');
        document.write('<tr>');
        document.write('  <td>&nbsp;</td>');
        document.write('  <td>&nbsp;</td>');
        document.write('  <td class="tac">&nbsp;</td>');
        document.write('  <td class="tac">&nbsp;</td>');
        document.write('  <td class="tar">&nbsp;</td>');
        document.write('  <td class="tar">&nbsp;</td>');
        if(dockind =='03' || dockind == '04'){
	        document.write('  <td class="align_center">&nbsp;</td>');
        }
        else{
			document.write('  <td class="tar">&nbsp;</td>');
			 document.write('  <td class="tar">&nbsp;</td>');
        }
        document.write('  <td class="tal brn">&nbsp;</td>');
        document.write('</tr>');
        document.write(']]></xsl:text>');
        if(i == BlankLine) { break; }
      } while(true)
    }
  }
 
  function Goremark3(re){
     if(re.length == 0)
    { document.write('<table>  	');
      document.write('<tr>  	');
      document.write('<td height="2">');
      document.write('</td>  ');
      document.write('</tr>');
      document.write('</table>  	');
    }else
    {document.write('<table>  	');
      document.write('<tr>');
      document.write('<td height="2"></td>');
      document.write('</tr>');
      document.write('<tr>');
      document.write('<td align="left" ><span style="font-size:12px;"><b>');
                      prn_txt(v_Remarks3);
      document.write('</b></span></td>');
      document.write('</tr>');
      document.write('</table>  	');
    }
  }
  

  function vformat(pColor){
    if(pColor == 'blue') {
      document.write(' <xsl:text disable-output-escaping="yes"><![CDATA[<strong>공급받는자</strong> 보관용]]></xsl:text> ');
    }else{
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[<strong>공급자</strong> 보관용]]></xsl:text>');
    }
  }

  function vChgCode(vcode){
       if( trim(vcode) == '' ){
           return '';
       }

       if(vcode == '01'){
          document.write("기재사항의 착오·정정");
       }else if(vcode == '02'){
           document.write("공급가액 변동");
       }else if(vcode == '03'){
           document.write("환입");
       }else if(vcode == '04'){
          document.write("계약의 해제");
       }else if(vcode == '05'){
           document.write("내국신용장 사후 개설");
       }else {
           document.write("착오에 의한 이중발급");
       }
  }

  function vTaxTitlePrint(ptaxType){
    if(ptaxType == '0101'){
      document.write("전자세금계산서");
    }else if(ptaxType == '0102'){
      document.write("전자세금계산서(영세율)");
    }else if(ptaxType == '0103'){
      document.write("전자세금계산서");
    }else if(ptaxType == '0104'){
      document.write("수입 세금계산서");
    }else if(ptaxType == '0105'){
      document.write("전자세금계산서(영세율)");
    }else if(ptaxType == '0201'){
      document.write("전자수정세금계산서");
    }else if(ptaxType == '0202'){
      document.write("전자수정세금계산서(영세율)");
    }else if(ptaxType == '0203'){
      document.write("전자수정세금계산서");
    }else if(ptaxType == '0204'){
      document.write("수정 수입 세금계산서");
    }else if(ptaxType == '0205'){
      document.write("전자수정세금계산서(영세율)");
    }else if(ptaxType == '0301'){
      document.write("전자계산서");
    }else if(ptaxType == '0303'){
      document.write("전자계산서");
    }else if(ptaxType == '0304'){
      document.write("수입 계산서");
    }else if(ptaxType == '0401'){
      document.write("수정 전자 계산서");
    }else if(ptaxType == '0403'){
      document.write("수정 위수탁 계산서");
    }else if(ptaxType == '0404'){
      document.write("수정 수입 계산서");
    }else{
      document.write("세금계산서(영세율)"); // Agent에서 사용
    }
  }

  function DemandPrint(pDemand){
    if(pDemand == '01') {
      document.write("영수");
    }else{
      document.write("청구");
    }
  }

  function splitRegNo(strRegNo){
    if(strRegNo.length == 10){
      document.write(strRegNo.substring(0,  3 )+"-"+strRegNo.substring(3,  5 )+"-"+strRegNo.substring(5,  10 ));
    }else if(strRegNo.length == 13) {
      document.write(strRegNo.substring(0,  6 )+"-"+strRegNo.substring(6,  13 ));
    } else {
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    }
  }

  function splitNtsNo(strNtsNo){
      //document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
      if(strNtsNo.length == 24){
      	document.write(strNtsNo.substring(0,  8 )+"-"+strNtsNo.substring(8,  16 )+"-"+strNtsNo.substring(16,  24 ));
      }
  }

  function splitMoney(money, seq){
    document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>' + money.substring(money.length - seq, money.length - seq + 1));
  }

  function makeYYMMDD(strDate){
    if(strDate.length == 8){
      document.write(strDate.substring(0, 4)+"/"+strDate.substring(4, 6)+"/"+strDate.substring(6, 8));
    }else{
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    }
  }

  function makeYear(strDate){
    if(strDate.length == 8){
      document.write(strDate.substring(0, 4));
    }else{
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    }
  }

  function prn_coregno(t) {
    if(trim(t).length == 0){
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    } else if(trim(t).length == 10){
      document.write(t.substring(0, 3) + '-' + t.substring(3, 5) + '-' + t.substring(5, 10));
    } else {
      document.write(t.substring(0, 6) + '-' + t.substring(6, 13));
    }
  }

  function makeMonth(strDate){
    if(strDate.length == 8){
      document.write(strDate.substring(4, 6));
    }else if(strDate.length == 4){
      document.write(strDate.substring(0, 2));
    }else if(strDate.length == 7){
      document.write(strDate.substring(4, 6));
    }else{
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    }
  }

  function makeDay(strDate){
    if(strDate.length == 8){
      document.write(strDate.substring(6, 8));
    }else if(strDate.length == 4){
      document.write(strDate.substring(2, 4));
    }else if(strDate.length == 7){
      document.write(strDate.substring(6, 7));
    }else{
      document.write('<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');
    }
  }

  function setRmk(rmk){
    document.write( rmk.replace("\n", "<br/>") ) ;
  }

  function ContactPrint() {
    <!--
        1208114879 : 동일방직
        1168140780 : 일신방직
        1318100356 : 동일레나운
        1208605491 : 동일드방레
        1028129258 : 교보핫트랙스
        위 4개 업체는 위수탁으로 보내도 위수탁자 정보가 빠진다. 
    -->
  	
		if(v_ShowUser != "false"){
		    if(pFormat == 'Broker') {
		    	if (!(v_BrokerBizregno =='1168140780' || v_BrokerBizregno =='1208114879' || v_BrokerBizregno =='1318100356' || v_BrokerBizregno =='1208605491' || v_BrokerBizregno =='1028129258'))
		    	{
		      	BrokerContactPrint(pColor);
		      } else 
		      {<!-- 일반포맷 담당자 출력 OK-->
		      	NormalContactPrint(pColor);
		      }
		    } 
		    else 
		    {<!-- 일반포맷 담당자 출력 OK-->
		      NormalContactPrint(pColor);
		    }
		} 
	}


						
  function NormalContactPrint(pColor) {
    <!-- 일반포맷 담당자 출력 OK-->
		document.write('	<div class="crpFoot">');
		document.write('	<table class="personTable" summary="공급자, 공급자, 수탁자등 구분별 담당자 정보를 제공합니다." width="656">');
		document.write('	<caption>담당자정보</caption>');
	if( trim(p_DmndName2) != '' || trim(p_DmndEmail2) != ''){
		
		document.write('	<colgroup><col width="16%" /><col width="28%" /><col width="28%" /><col width="*%" /></colgroup>');
		document.write('	<thead>');
		document.write('	<tr>');
		document.write('	<th scope="col">구분</th>');
		document.write('	<th scope="col">공급자</th> ');
		document.write('	<th scope="col">공급받는자</th>');
		document.write('	<th scope="col" class="brn">공급받는자2</th>');
		document.write('	</tr>');
		document.write('	</thead>');
	} else {
		
	  	document.write('	<colgroup><col width="17%" /><col width="41%" /><col width="*%" /></colgroup>');
		document.write('	<thead>');
		document.write('	<tr>');
		document.write('	<th scope="col">구분</th>');
		document.write('	<th scope="col">공급자</th> ');
		document.write('	<th scope="col" class="brn">공급받는자</th>');
		document.write('	</tr>');
		document.write('	</thead>');
		
	}
	document.write('	<tbody>');
	document.write('	<tr>');
	document.write('	<th scope="row">담당자</th>');
	document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:DefinedContact/tbs:PersonNameText"/></td>');	
	if( trim(p_DmndName2) != '' || trim(p_DmndEmail2) != ''){
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:PersonNameText"/></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:PersonNameText"/></td>');
	}
	else{
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:PersonNameText"/></td>');
	}
	document.write('	</tr>');
	
	document.write('	<tr>');
	document.write('	<th scope="row">연락처</th>');
	document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:DefinedContact/tbs:TelephoneCommunication"/></td>');
	if( trim(p_DmndName2) != '' || trim(p_DmndEmail2) != ''){
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:TelephoneCommunication"/></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:TelephoneCommunication"/></td>');
	}
	else{
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:TelephoneCommunication"/></td>');
	}
	document.write('	</tr>');
	
	document.write('	<tr>');
	document.write('	<th scope="row">e-mail</th>');
	document.write('	<td><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:DefinedContact/tbs:URICommunication"/></a></td>');
	if( trim(p_DmndName2) != '' || trim(p_DmndEmail2) != ''){
	  document.write('	<td><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:URICommunication"/></a></td>');
		document.write('	<td class="brn"><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:URICommunication"/></a></td>');
	}
	else{
		document.write('	<td class="brn"><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:URICommunication"/></a></td>');
	}
	document.write('	</tr>');	
	document.write('	</tbody>');
	document.write('	</table>');
	document.write('	</div>');
	

}

  function BrokerContactPrint(pColor) {
    <!-- 위수탁 포맷 담당자 출력 OK-->
    	document.write('	<div class="crpFoot">');
		document.write('	<table class="personTable" summary="공급자, 공급자, 수탁자등 구분별 담당자 정보를 제공합니다." width="656">');
		document.write('	<caption>담당자정보</caption>');
	if( trim(p_DmndName2) != '' ){
		document.write('	<colgroup><col width="12%" /><col width="22%" /><col width="22%" /><col width="22%" /><col width="*%" /></colgroup>');
		document.write('	<thead>');
		document.write('	<tr>');
		document.write('	<th scope="col">구분</th>');
		document.write('	<th scope="col">공급자</th> ');
		document.write('	<th scope="col">공급받는자</th>');
		document.write('	<th scope="col">공급받는자2</th>');
		document.write('	<th scope="col" class="brn">수탁자</th>');
		document.write('	</tr>');
		document.write('	</thead>');
	} else {
	  document.write('	<colgroup><col width="16%" /><col width="28%" /><col width="28%" /><col width="*%" /></colgroup>');
		document.write('	<thead>');
		document.write('	<tr>');
		document.write('	<th scope="col">구분</th>');
		document.write('	<th scope="col">공급자</th> ');
		document.write('	<th scope="col">공급받는자</th>');
		document.write('	<th scope="col" class="brn">수탁자</th>');
		document.write('	</tr>');
		document.write('	</thead>');
		
	}
	document.write('	<tbody>');
	document.write('	<tr>');
	document.write('	<th scope="row">담당자</th>');
	document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:DefinedContact/tbs:PersonNameText"/></td>');	
	if( trim(p_DmndName2) != '' ){
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:PersonNameText"/></td>');
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:PersonNameText"/></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:DefinedContact/tbs:PersonNameText"/></td>');
	}
	else{
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:PersonNameText"/></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:DefinedContact/tbs:PersonNameText"/></td>');
	}
	document.write('	</tr>');
	
	document.write('	<tr>');
	document.write('	<th scope="row">연락처</th>');
	document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:DefinedContact/tbs:TelephoneCommunication"/></td>');
	if( trim(p_DmndName2) != '' ){
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:TelephoneCommunication"/></td>');
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:TelephoneCommunication"/></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:DefinedContact/tbs:TelephoneCommunication"/></td>');
	}
	else{
		document.write('	<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:TelephoneCommunication"/></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:DefinedContact/tbs:TelephoneCommunication"/></td>');
	}
	document.write('	</tr>');
	
	document.write('	<tr>');
	document.write('	<th scope="row">e-mail</th>');
	document.write('	<td><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:DefinedContact/tbs:URICommunication"/></a></td>');
	if( trim(p_DmndName2) != '' ){
	  document.write('	<td><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:URICommunication"/></a></td>');
		document.write('	<td><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SecondaryDefinedContact/tbs:URICommunication"/></a></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:DefinedContact/tbs:URICommunication"/></td>');
	}
	else{
		document.write('	<td><a class="link" href="mailto:test@test.com"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:PrimaryDefinedContact/tbs:URICommunication"/></a></td>');
		document.write('	<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:DefinedContact/tbs:URICommunication"/></td>');
	}
	document.write('	</tr>');	
	document.write('	</tbody>');
	document.write('	</table>');
	document.write('	</div>');
	}

</script>



<!-- 전체 세금계산서 색을 밑에 div class에서 결정한다. 값이suRed이면 빨강 그렇지 않으면 파랑이다. -->
<div id="previewWrap" class="{$newColor}">
						<div class="previewCont">
							
							<!-- 타이틀, 일련번호, 승인번호 -->
							<h2><script type="text/javascript"> vTaxTitlePrint(v_number); </script><span>(<script type="text/javascript"> vformat('<xsl:value-of select ="$pColor"/>');</script>)</span></h2>
							
							<!-- 문서 상태 표시 -->							
							<xsl:if test="string-length($statusInfo) > 2">
								<!--
								<p class="progress"><img src="{$url_stateImg}" alt="pSignYN" /></p>
								 현재 영수증의 상태를 나타냅니다. alt 안에 현재 진행단계를 넣어주세요
									1. 공급받는자취소요청(progress01) 
									2. 관리자취소요청(progress02) 
									3. 관리자 서명요청(progress03) 
									4. 발급진행중(progress04) 
									5. 발급대기(progress05) 
									6. 발행예정(progress06) 
									7.미승인(progress07) 
									8.발행예정진행중(progress08)
									<img src="{$url_stateImg}" />
								-->
								<p class="progress01"><script type="text/javascript"> BackPng(); </script></p>
							</xsl:if>
							
<!-- 스탬프 -->
							<!-- 인감 표시-->
							<xsl:if test="string-length($seal) > 2">
								<p class="stamp"><img width="60" src="{$seal}" alt="공급자직인" /></p>
								</xsl:if>
<!-- 스탬프 -->
										
							<dl class="previewTinfo">
								<dt>일련번호</dt>
								<dd class="tac"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:ExchangedDocument/tbs:ReferencedDocument/tbs:ID"/></dd>
								<dt class="bbn">승인번호</dt>
								<dd class="bbn tac"><script type="text/javascript">splitNtsNo(v_IssueCode);</script></dd>
							</dl>
							
							<!-- 공급자, 공급받는자 정보 -->
							<xsl:choose>
								<!-- 개인일때 디자인안됐음-->
						    <xsl:when test="$Personal_YN = 'Y'">    
						    	<div class="crpTop">
						    	<table class="tbl_pmtable" width="100%">
						    			<colgroup>
						    				<col width="3%" />
						    				<col width="8%" />
						    				<col width="15%" />
						    				<col width="8%" />
						    				<col width="15%" />
						    				<col width="3%" />
						    				<col width="8%" />
						    				<col width="*" />
						    			</colgroup>
											<tr>
												<td class="Ftit bln" rowspan="5"><strong>공급자</strong></td>
												<td class="Stit Bbtn"><p class="Bbln">등록번호</p></td>
												<td colspan="3" class="Bbtn Bbrn"><strong><script type="text/javascript">splitRegNo(v_SuppBizregno);</script></strong></td>
												<td class="Ftit brn" rowspan="5" style="border-left:1px solid #b3bacc;"><strong>공급받는자</strong></td>
												<td class="Stit Bbtn"><p class="Bbln">등록번호</p></td>
												<td colspan="3" class="Bbtn Bbrn"><strong><script type="text/javascript">splitRegNo(v_DmndBizregno);</script></strong></td>
											</tr>
											<tr>
												<td class="Stit nbln Bbbn"><p class="Bbln">상호</p></td>
												<td colspan="3" class="Bbbn Bbrn"><strong><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:NameText"/></strong></td>
												<td class="Stit nbln Bbbn"><p class="Bbln">성명</p></td>
												<td colspan="3" class="Bbbn Bbrn">
													<strong>
														<!-- 개인일때 대표자명이 없는 경우 상호명을 보여줌 -->
																	        <xsl:variable name="per_NameText" select="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SpecifiedPerson/tbs:NameText"/><!-- 상호명  -->
																	        <xsl:choose>
																						<xsl:when test="string-length($per_NameText)">
																	          	<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>
																	          	<xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SpecifiedPerson/tbs:NameText"/>
																	          </xsl:when>
																						<xsl:otherwise>
																	          	<xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>
																	          	<xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:NameText"/>
																	          </xsl:otherwise>
																					</xsl:choose>
													</strong>
												</td>
											</tr>
											<tr>
												<td class="Stit">대표자</td>
												<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:SpecifiedPerson/tbs:NameText"/></td>
												<td class="Stit">종사업장 <br />등록번호</td>
												<td><script type="text/javascript">prn_txt('<xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:SpecifiedOrganization/tbs:TaxRegistrationID"/>');</script></td>
												<td class="Stit" rowspan="3">주소</td>
												<td rowspan="3" colspan="3"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SpecifiedAddress/tbs:LineOneText"/></td>
											</tr>
											<tr>
												<td class="Stit">사업장<br />주소</td>
												<td colspan="3"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:SpecifiedAddress/tbs:LineOneText"/></td>
											</tr>
											<tr>
												<td class="Stit">업태</td>
												<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:TypeCode"/></td>
												<td class="Stit">종목</td>
												<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:ClassificationCode"/></td>
											</tr>
										</table>
										
										
									</div>
						    </xsl:when>

						    
								<!-- 사업자일때 OK -->
						    <xsl:otherwise>
								<div class="crpTop">
								<table class="tbl_pmtable" width="100%">
									<colgroup>
										<col width="3%" />
										<col width="8%" />
										<col width="15%" />
										<col width="8%" />
										<col width="15%" />
										<col width="3%" />
										<col width="8%" />
										<col width="15%" />
										<col width="8%" />
										<col width="*" />
									</colgroup>
									<tr>
										<td class="Ftit bln" rowspan="5"><strong>공급자</strong></td>
										<td class="Stit Bbtn"><p class="Bbln">등록번호</p></td>
										<td colspan="3" class="Bbtn Bbrn"><strong><script type="text/javascript">splitRegNo(v_SuppBizregno);</script></strong></td>
										<td class="Ftit" rowspan="5" style="border-left:1px solid #b3bacc;"><strong>공급받는자</strong></td>
										<td class="Stit Bbtn"><p class="Bbln">등록번호</p></td>
										<td colspan="3" class="Bbtn Bbrn"><strong><script type="text/javascript">splitRegNo(v_DmndBizregno);</script></strong></td>
									</tr>
									<tr>
										<td class="Stit nbln Bbbn"><p class="Bbln">상호</p></td>
										<td colspan="3" class="Bbbn Bbrn"><strong><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:NameText"/></strong></td>
										<td class="Stit nbln Bbbn"><p class="Bbln">상호</p></td>
										<td colspan="3" class="Bbbn Bbrn"><strong><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:NameText"/></strong></td>
									</tr>
									<tr>
										<td class="Stit">대표자</td>
										<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:SpecifiedPerson/tbs:NameText"/></td>
										<td class="Stit">종사업장 <br />등록번호</td>
										<td class="nbrn"><script type="text/javascript">prn_txt('<xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:SpecifiedOrganization/tbs:TaxRegistrationID"/>');</script></td>
										<td class="Stit">대표자</td>
										<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SpecifiedPerson/tbs:NameText"/></td>
										<td class="Stit">종사업장 <br />등록번호</td>
										<td><script type="text/javascript">prn_txt('<xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SpecifiedOrganization/tbs:TaxRegistrationID"/>');</script></td>
									</tr>
									<tr>
										<td class="Stit">사업장<br/>주소</td>
										<td colspan="3"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:SpecifiedAddress/tbs:LineOneText"/></td>
										<td class="Stit">사업장<br/>주소</td>
										<td colspan="3"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:SpecifiedAddress/tbs:LineOneText"/></td>
									</tr>
									<tr>
										<td class="Stit">업태</td>
										<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:TypeCode"/></td>
										<td class="Stit">종목</td>
										<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoicerParty/tbs:ClassificationCode"/></td>
										<td class="Stit">업태</td>
										<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:TypeCode"/></td>
										<td class="Stit">종목</td>
										<td><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:InvoiceeParty/tbs:ClassificationCode"/></td>
									</tr>
								</table>	
							</div>
							</xsl:otherwise>
		  				</xsl:choose>
		  				
		  				<xsl:choose>
				<!-- 위수탁 디자인 OK-->
		    			<xsl:when test="$pFormat = 'Broker'">
	
			    <!-- 위수탁자 정보 (예외처리 하드코딩 포함) -->
					<script type="text/javascript">
					   var brokerNo1 = v_BrokerBizregno;
					
					   if(!(brokerNo1 == '1168140780' || brokerNo1 == '1208114879' || brokerNo1 =='1318100356' || brokerNo1 =='1208605491' || brokerNo1 =='1028129258'))
					   {
					    document.write('        <table class="bailTable" summary="등록번호, 상호, 종사업장번호등 수탁자에 대한 정보를 제공합니다." width="656">');
							document.write('        		<caption>수탁자</caption>');
							document.write('        		<colgroup>');
							document.write('        			<col width="12%" />');
							document.write('        			<col width="9%" />');
							document.write('        			<col width="19%" />');
							document.write('        			<col width="9%" />');
							document.write('        			<col width="*" />');
							document.write('        			<col width="9%" />');
							document.write('        			<col width="16%" />');
							document.write('        		</colgroup>');
							document.write('        		<tbody>');
							document.write('        			<tr>');
							document.write('        				<th id="cr17">수탁자</th>');
							document.write('        				<th id="cr18" headers="cr17">등록번호</th>');
							document.write('        				<td headers="cr17 cr18">'); prn_coregno(v_BrokerBizregno);document.write('</td>');
							document.write('        				<th id="cr19" headers="cr17">상호</th>');
							document.write('        				<td headers="cr19 cr17">');prn_txt(v_BrokerCoName);document.write('</td>');
							document.write('        				<th id="cr20" headers="cr17">종사업장<br />등록번호</th>');
							document.write('        				<td headers="cr17 cr20" class="brn">');prn_txt('<xsl:value-of select ="//tbs:TaxInvoiceTradeSettlement/tbs:BrokerParty/tbs:SpecifiedOrganization/tbs:TaxRegistrationID"/>');document.write('</td>');
							document.write('        			</tr>');
							document.write('        		</tbody>');
							document.write('        	</table>');
					    }
					</script>
					</xsl:when>
			  		</xsl:choose>
		  
		  
							<div class="crpmid">
								<table summary="작성일자, 공급가액, 세액, 수정사유등 금액정보를 제공합니다." width="656">
									<caption>금액</caption>
									<colgroup>									 									 
						  	 	<xsl:choose>
								    <xsl:when test="$oFormat = '0301' ">
								    		<col width="86px" /> 
											<col width="150px" />
											<col width="150px" />										
											<col width="*" />																				
							    	</xsl:when>
							    	<xsl:when test="$oFormat = '0303' ">
								    		<col width="86px" /> 
											<col width="150px" />
											<col width="150px" />										
											<col width="*" />	
							    	</xsl:when>
							    	<xsl:when test="$oFormat = '0304' ">
								    		<col width="86px" /> 
											<col width="150px" />
											<col width="150px" />										
											<col width="*" />	
							    	</xsl:when>
							    	<xsl:when test="$oFormat = '0401' ">
								    		<col width="86px" /> 
											<col width="150px" />
											<col width="150px" />										
											<col width="*" />	
							    	</xsl:when>
							    	<xsl:when test="$oFormat = '0403' ">
								    		<col width="86px" /> 
											<col width="150px" />
											<col width="150px" />										
											<col width="*" />	
							    	</xsl:when>
							    	<xsl:when test="$oFormat = '0404' ">
								    		<col width="86px" /> 
											<col width="150px" />
											<col width="150px" />										
											<col width="*" />	
							    	</xsl:when>
								    <xsl:otherwise>
								    		<col width="70px" /> 
											<col width="110px" />
											<col width="110px" />
											<col width="150px" />
											<col width="*" />
							    	</xsl:otherwise>
			  					</xsl:choose>
										</colgroup>
										<thead>
											<tr class="btn">
												<th scope="col">작성일자</th>
												<th scope="col">공급가액</th>
												
												<script type="text/javascript">
													if (dockind == '03' || dockind == '04')
													{
													 document.write('');
													}else{
													 document.write('				<th scope="col">세액</th>');
			
													}
												 </script>	
												<th scope="col">수정사유</th>
												<th scope="col">당초승인번호</th>
												
											</tr>
									</thead>
									<tbody>																									
										<tr>
											<td><script type="text/javascript">makeYYMMDD('<xsl:value-of select ="//tbs:TaxInvoiceDocument/tbs:IssueDateTime"/>' );</script></td>
											<td class="tar"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><script type="text/javascript"> document.write(comma_num(v_ChargeAmount));</script></td>
											
											<script type="text/javascript">										
												if (dockind == '03' || dockind == '04')
												{
												 document.write('');
												}else{
												 document.write('				<td class="tar"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text>');document.write(comma_num(v_TotalTax)); document.write('</td>');
												}
											 </script>
											<td align="center"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><script type="text/javascript"> vChgCode(v_ChgCode);prn_txt('');</script></td>										
											
											<td align="center"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of  select ="//tbs:TaxInvoiceDocument/tbs:OriginalIssueID"/></td>
										</tr>								
									</tbody>
								</table>
								<table class="noteTable" summary="비고정보를 제공합니다." width="656">
									<caption>비고</caption>
									<colgroup>
										<col width="86px" />
										<col width="*" />
									</colgroup>
									<tbody>
										<tr>
											<th scope="row">비고</th>
											<td class="brn"><xsl:text disable-output-escaping="yes"><![CDATA[&nbsp;]]></xsl:text><xsl:value-of  select ="//tbs:TaxInvoiceDocument/tbs:DescriptionText"/></td>
										</tr>
									</tbody>
								</table>
								
								
								<table class="itemTable" summary="월,일,품목,규격,수량,단가,공급가액,세액,비고 등 품목에대한 정보를 제공합니다." width="656">
									<caption>품목</caption>
									<colgroup>
										<col width="19px" />
										<col width="20px" />
										<col width="*" />
										<col width="49px" />
										<col width="49px" />
										<col width="70px" />
										
										
										
										<xsl:choose>
										    <xsl:when test="$oFormat = '0301' ">
										    		<col width="127px" /> 
													<col width="127px" />
									    	</xsl:when>
									    	<xsl:when test="$oFormat = '0303' ">
										    		<col width="127px" /> 
													<col width="127px" />
									    	</xsl:when>
									    	<xsl:when test="$oFormat = '0304' ">
										    		<col width="127px" /> 
													<col width="127px" />
									    	</xsl:when>
									    	<xsl:when test="$oFormat = '0401' ">
										    		<col width="127px" /> 
													<col width="127px" />
									    	</xsl:when>
									    	<xsl:when test="$oFormat = '0403' ">
										    		<col width="127px" /> 
													<col width="127px" />
									    	</xsl:when>
									    	<xsl:when test="$oFormat = '0404' ">
										    		<col width="127px" /> 
													<col width="127px" />
									    	</xsl:when>
										    <xsl:otherwise>
										    		<col width="85px" />
													<col width="84px" />
													<col width="85px" />
									    	</xsl:otherwise>
					  				</xsl:choose>
					  				
					  				
										
										
									</colgroup>
									<thead>
										<tr class="btn">
											<th scope="col">월</th>
											<th scope="col">일</th>
											<th scope="col">품목</th>
											<th scope="col">규격</th>
											<th scope="col">수량</th>
											<th scope="col">단가</th>
											
											
											
											
									<!-- dockind == '03' dockind가 뭐지..... 일때 디자인미정-->
									<script type="text/javascript">
										if (dockind == '03' || dockind == '04')
										{
										 document.write('				<th scope="col">공급가액</th>');
										 document.write('				<th scope="col" class="brn">비고</th>');
										}else{
										 document.write('				<th scope="col">공급가액</th>');
										 document.write('				<th scope="col">세액</th>');
										 document.write('				<th scope="col" class="brn">비고</th>');
										}
									 </script>
						          
						          
										</tr>
									</thead>
									<tbody>
									<xsl:for-each select="//tbs:TaxInvoiceTradeLineItem">
										<tr>
											<td><script type="text/javascript">makeMonth('<xsl:value-of select="tbs:PurchaseExpiryDateTime"/>' );</script></td>
											<td><script type="text/javascript">makeDay('<xsl:value-of select="tbs:PurchaseExpiryDateTime"/>' );</script></td>
											<td><script type="text/javascript">prn_txt('<xsl:value-of select="tbs:NameText"/>');</script></td>
											<td class="tac"><script type="text/javascript">prn_txt('<xsl:value-of select="tbs:InformationText"/>');</script></td>
											<td class="tac"><script type="text/javascript">prn_comm('<xsl:value-of select="tbs:ChargeableUnitQuantity"/>');</script></td>
											<td class="tar"><script type="text/javascript">prn_comm('<xsl:value-of select="tbs:UnitPrice/tbs:UnitAmount"/>');</script></td>
											<script type="text/javascript">if (dockind == '03' || dockind == '04'){
												document.write('        <td class="tar">'); prn_comm('<xsl:value-of select="tbs:InvoiceAmount"/>'); document.write('</td>');
												document.write('        <td class="tal brn">'); prn_txt('<xsl:value-of select="tbs:DescriptionText"/>');  document.write('</td>');
											}else{
												document.write('        <td class="tar">'); prn_comm('<xsl:value-of select="tbs:InvoiceAmount"/>'); document.write('</td>');
												document.write('        <td class="tar">'); prn_comm('<xsl:value-of select="tbs:TotalTax/tbs:CalculatedAmount"/>'); document.write('</td>');
												document.write('        <td class="tal brn">'); prn_txt('<xsl:value-of select="tbs:DescriptionText"/>');  document.write('</td>');
											}
											</script>
										</tr>
									</xsl:for-each>
									<!-- 공백 아이템 목록 생성 -->
    								<script type="text/javascript"> BlankItemListPrint('<xsl:value-of select="4 - $ItemLine"/>'); </script>
									</tbody>
								</table>
							</div>
							<div class="crpsum">
								 <table summary="합계금액, 현금,수표,어음,외상미수금 등의 총금액정보를 제공합니다." width="500">
									<caption>총금액</caption>
									<colgroup>
										<col width="100px" />
										<col width="100px" />
										<col width="100px" />
										<col width="100px" />
										<col width="100px" />
									</colgroup>
									<thead>
										<tr>
											<th scope="col">합계금액</th>
											<th scope="col">현금</th>
											<th scope="col">수표</th>
											<th scope="col">어음</th>
											<th scope="col">외상미수금</th>
										</tr>
									</thead>
									<tbody>
										<tr>
											<script type="text/javascript"> PaymentMethodPrint(); </script>
											<!-- 
											<td class="tar">&nbsp;이 금액을 <strong><script type="text/javascript">DemandPrint('<xsl:value-of select ="//tbs:TaxInvoiceDocument/tbs:PurposeCode"/>');</script></strong>함&nbsp;</td>
											 -->
										</tr>
									</tbody>
								 </table>
								 <p>이 금액을 <strong><script type="text/javascript">DemandPrint('<xsl:value-of select ="//tbs:TaxInvoiceDocument/tbs:PurposeCode"/>');</script></strong>함</p>
							</div>
						</div>
						<!-- 비고3 나오기 -->
						<script type="text/javascript">Goremark3(v_Remarks3);</script>
						
						
						<!-- 
						<div class="crpFoot">
							<table class="personTable" summary="공급자, 공급자, 수탁자등 구분별 담당자 정보를 제공합니다." width="656">
								<caption>담당자정보</caption>
								 담당자 표시   
								<script type="text/javascript"> ContactPrint(); </script> 
							</table>
						</div>
						 -->
						
						<!--  담당자 표시-->   
								<script type="text/javascript"> ContactPrint(); </script> 
							
						
						<p class="RfMark mT08">본 인쇄물은 국세청 고시 기준에 따라 트러스빌(<a href="http://trusbill.or.kr" target="_blank">www.trusbill.or.kr</a>)에서 발행된 전자세금계산서입니다.</p>
						
					</div>
					
					
</xsl:template>
</xsl:stylesheet>