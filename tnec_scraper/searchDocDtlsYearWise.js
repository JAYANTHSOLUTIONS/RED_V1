async function searchDocDtlsYearWise()
{	
	var ecNewFlowApplicableFlag = true
    if(checkMandSearchDocYearWise())
   	{
    	const villageDetailsValid = await getVillageDetails();
    	if(villageDetailsValid && encryptPlotFlat())
    		{
    		$("#sroName").val($("#cmb_SroName :selected").text());
    		sro = $("#cmb_SroName :selected").val();
       	    var captchaVal=$("#txt_Captcha").val();
			zone = $("#cmb_Zone :selected").val();
    		dist = $("#cmb_District :selected").val();
    		oldSurvey = $("#txt_oldSurveyNo").val();
    		conv_ext= $("#txt_convExtent").val();
    		ttlExt =  $("#txt_totalExtent").val();
    		undShare = $("#txt_undivShare").val();
    		buildArea = $("#txt_buildUpArea").val();
    		tsNo = $("#txt_TSNo").val();
    		oldDoor = $("#txt_oldDoorNo").val();
    		own = $("#txt_owner").val();
    		ownFather = $("#txt_ownerFather").val();
    		schdlrmrk = $("#txt_scheduleRemark").val();
    		regdoc = $("#txt_regDoc").val();
  
    		$("#captcha_val").val(encodeURIComponent(captchaVal));
    	
    	  
    	
    	  document.getElementById("hdnCmnDDMMYYlert").value = "";
    	  document.getElementById("hdnCmnDateAlert").value = "";
    	  document.getElementById("hdn_year").value = "";
    	  document.getElementById("SpecialCharAndSpaceAlert").value = "";
 
    	  
    		var url=urlHome+"?requestType=ApplicationRH&actionVal=searchDocYearWise&screenId=8400001&divId=searchComponentSection&isPlotFlatWise=false&_csrf="+getAjaxSecurityToken()+"&"+$.param($('#EncumbranceCertificateForm').serializeArray());        
    		updateContainer(url,"",'searchComponentSection');     
    		}
      
    }
}