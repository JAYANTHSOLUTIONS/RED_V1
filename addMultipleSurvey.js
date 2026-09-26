function addMultipleSurvey()
{
    var flag = true;
    if($('#txt_SurveyNo').val() == "")
    {
        $('#incSurveyNo').html('தயவுசெய்து புல எண்ணினை உள்ளிடவும்');
        flag = false;
    }
    else
    {
        $('#incSurveyNo').html('');
    }
	if($('#cmb_Village').val() == '-1')
	{
		$('#incCmbVillage').html('தயவுசெய்து கிராமத்தினைத் தெரிவு செய்யவும்		');
		flag = false;
	}
	else
	{
	    $('#incCmbVillage').html('');
	}
	
	
    if(flag)
     {
		flag = validateSubDivNo();
		flag=validateParentSurvey();
		flag = validateMultiVillage();
     }
    
    if(!flag)
    {
		return true;
    }
    
    $("#hdnZone").val($("#cmb_Zone").val());
    $("#hdnDistrict").val($("#cmb_District").val());
    $("#hdnSroName").val($("#cmb_SroName").val());
    $("#cmb_Zone").prop("disabled",true);
    $("#cmb_District").prop("disabled",true);
    $("#cmb_SroName").prop("disabled",true);

    var tbody = document.getElementById('multiAddSurvey').getElementsByTagName('tbody')[0];
	var rowIndex = tbody.rows.length;
	var row = tbody.insertRow(rowIndex);
	row.style.wordBreak="break-all";
	var cell1 = row.insertCell(0);
	var cell2 = row.insertCell(1);
	var cell3 = row.insertCell(2);
	var cell4 = row.insertCell(3);
	
	var villageName=cmb_Village.options[cmb_Village.selectedIndex].text;
	var villageId=cmb_Village.options[cmb_Village.selectedIndex].value;
	
	if(villageId!=-1)
	{
		cell1.innerHTML=villageName;
	}
	var SurveyNo = document.getElementById("txt_SurveyNo").value;
	cell2.innerHTML = SurveyNo;

	var SubDivNo = document.getElementById("txt_SubDivisionNo").value;
	if(SubDivNo=="" )
	{
		cell3.innerHTML="--";
	}
	else
	{
		cell3.innerHTML=SubDivNo;
	}

	
	
	var imgDel = document.createElement('img');
	imgDel.onclick = function() {return removeRow(this);};
	imgDel.src = "images/DeleteIcon1.gif";

	var element1 = document.createElement("input");
	element1.type = "hidden";
	element1.name = "multi_SurveyNo";
	element1.id = "txt_SurveyNo_"+gridCounter;
	element1.value = SurveyNo;

	var element2 = document.createElement("input");
	element2.type = "hidden";
	element2.name = "multi_SubDivisionNo";
	element2.id = "txt_SubDivisionNo_"+gridCounter;
	element2.value = SubDivNo;
	var element3 = document.createElement("input");
	element3.type = "hidden";
	element3.name = "multi_cmb_Village";
	element3.id = "cmb_Village_"+gridCounter;
	element3.value = $('#cmb_Village').val();

	cell4.appendChild(imgDel);
	cell4.appendChild(element1);
	cell4.appendChild(element2);
	cell4.appendChild(element3);
	gridCounter++;
	document.getElementById("txt_SurveyNo").value = "";
	document.getElementById("txt_SubDivisionNo").value = "";
	$("#cmb_Village option[value='-1']").prop('selected', true);
	$('#incMultiSurvey').html('');
	$('#multiAddSurvey').show();
}