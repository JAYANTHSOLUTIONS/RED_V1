// validateFromDate
function validateFromDate()
		{
		var flag=true;
		flag=checkFutureDate('txt_PeriodStartDt','incRegDateFrom');
		return flag;
		}

// validateToDate
function validateToDate()
{

var flag=true;
	var FromDate = document.getElementById("txt_PeriodStartDt").value;

	var ToDate = document.getElementById("txt_PeriodEndDt").value;
	var yy1 = ToDate.substr(7, 4);
	var month1 = ToDate.substr(3, 3);
	var date1 = ToDate.substr(0, 2);
	var current_date = new Date();
	var yy = FromDate.substr(7, 4);
	var month = FromDate.substr(3, 3);
	var date = FromDate.substr(0, 2);

	month1=getMonthNo(month1);
	month=getMonthNo(month);
	//flag=validateEndDate();
	if(flag)
	{
	flag=checkFutureDate('txt_PeriodEndDt','incRegDateTo');
	}
	if (ToDate != null && ToDate !== "") {
		if (yy > yy1) {
			document.getElementById("incRegDateTo").innerHTML='முடிவு தேதி தொடக்க தேதியினை விட குறைவாக இருக்க கூடாது';
			document.getElementById('incRegDateTo').style.display = "";
			 document.getElementById("txt_PeriodEndDt").value="";
	/* 	 $("#my_doc_to_dt").focus(); */
			flag=false;

		}


		if (yy == yy1) {
			if (month > month1) {
				document.getElementById("incRegDateTo").innerHTML='முடிவு தேதி தொடக்க தேதியினை விட குறைவாக இருக்க கூடாது';
				document.getElementById('incRegDateTo').style.display = "";
				document.getElementById("txt_PeriodEndDt").value="";
			  /* $("#my_doc_to_dt").focus(); */
				flag=false;
			}
		}
		if (month - month1 == 0) {
			if(yy==yy1)
				{
				if (date > date1) {
					document.getElementById("incRegDateTo").innerHTML='முடிவு தேதி தொடக்க தேதியினை விட குறைவாக இருக்க கூடாது';
					document.getElementById('incRegDateTo').style.display = "";
					document.getElementById("txt_PeriodEndDt").value="";
					/* $("#my_doc_to_dt").focus(); */
					flag=false;
				}
				}


		}

	}
	if(flag)
	{
	$("#incRegDateTo").html("");
	}
	  return flag;
}