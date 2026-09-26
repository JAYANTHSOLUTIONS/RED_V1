function checkMandSearchDocYearWise()
{
	
	var flag = true;

	if($('#cmb_Zone').val() == '-1')
	{
		$('#incCmbZone').html('தயவுசெய்து மண்டலத்தினைத் தெரிவு செய்யவும் 				');
		flag = false;
	}
	else
	{
	    $('#incCmbZone').html('');
	}

	if($('#cmb_District').val() == '-1')
	{
		$('#incCmbDistrict').html('தயவுசெய்து மாவட்டத்தினைத் தெரிவு செய்யவும் 		');
		flag = false;
	}
	else
	{
	    $('#incCmbDistrict').html('');
	}

	if($('#cmb_SroName').val() == '-1')
	{
		$('#incCmbSROName').html('தயவுசெய்து சார்பதிவாளர் அலுவலகத்தினை தெரிவு செய்யவும்');
		flag = false;
	}
	else
	{
	    $('#incCmbSROName').html('');
	}

	//addition started pragnesh-7896
	if($('#cmb_RevenueDistrict').val() == '-1')
	{
		$('#incCmbRevenueDistrict').html('தயவுசெய்து வருவாய் மாவட்டதினைத் தெரிவு செய்யவும்');
		flag = false;
	}
	else
	{
	    $('#incCmbRevenueDistrict').html('');
	}

	if($('#cmb_RevenueTaluka').val() == '-1')
	{
		$('#incCmbRevenueTaluka').html('தயவுசெய்து வருவாய் தாலுகாவைத் தெரிவு செய்யவும்');
		flag = false;
	}
	else
	{
	    $('#incCmbRevenueTaluka').html('');
	}
	//addition ended pragnesh-7896
	if($('#txt_PeriodStartDt').val()=='')
	{
		
		$('#incRegDateFrom').html('வில்லங்கச் சான்று கால ஆரம்ப நாளினை தயவுசெய்து தெரிவு செய்யவும்');
		$('#incRegDateFrom').show();
		flag = false;
	}
	else
	{
		$('#incRegDateFrom').html('');
	}

	if($('#txt_PeriodEndDt').val()=='')
	{
		
		$('#incRegDateTo').html('வில்லங்கச் சான்று கால முடிவு நாளினை தயவுசெய்து தெரிவு செய்யவும்');
		$('#incRegDateTo').show();
		flag = false;
	}
	else
	{
		$('#incRegDateTo').html('');
	}
	
	if($('#txt_convExtent').val() == '')
	{
		$('#alert_convExtent').html('Please enter Conveyed Extent.');
		flag = false;
	}
	else
	{
	    $('#alert_convExtent').html('');
	}
	
	var tbody = document.getElementById('multiAddSurvey').getElementsByTagName('tbody')[0];
	var rowIndex = tbody.rows.length;

	if(rowIndex == 0)
	{
	    $('#incMultiSurvey').html('தயவுசெய்து குறைந்தபட்சம் ஏதேனும் ஒரு புல விவரத்தினைச் சேர்க்கவும் ');
	    flag = false;
	}
	else
	{
	    $('#incMultiSurvey').html('');
	}

	if(!flag){
		$("#viewECData .alertmsg").css("display","block");
		}else{
			$("#viewECData .alertmsg").css("display","none");
			}

	if(!validateCaptcheForEc())
	{
		flag=false;
	}
	if(!(validateFromDate() && validateToDate()))
	{
		flag=false;
	}
	

	return flag;
}