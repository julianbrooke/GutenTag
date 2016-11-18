var subcorpus_count =0;
var active_subcorpus =-1;
var fork_clicked ='none'
var g_id = Math.random().toString().substring(2,8);


is_safari = /Version\/[\d\.]+.*Safari/.test(navigator.userAgent)
if (is_safari) {
	alert("We have detected you are using Safari, which is not officially supported. GutenTag may work, but if you are exporting large corpora it may take longer than normal (your browser may freeze for upwards of ten minutes at the end of the process) and you will have to rename the downloaded file (Untitled) manually (your filename must have the .zip file extension to be opened). We recommend you use Chrome or Firefox.");
}

function CreateXmlHttpObject( )
{
	var xmlHttpRqst = undefined;
	try
	{
		xmlHttpRqst = new XMLHttpRequest( );
	}
	catch (e)
	{
		try
		{
			xmlHttpRqst = new ActiveXObject( "Msxml2.XMLHTTP" );
		}
		catch (e)
		{
			try
			{
				xmlHttpRqst = new ActiveXObject( "Microsoft.XMLHTTP" );
			}
			catch (e)
			{
				xmlHttpRqst = undefined;
			}
		}
	}
	
	return xmlHttpRqst;
}

function toggle_display(element) {
	//element = document.getElementById(id);
	if (element.style.display == '') {
		if (element.id.substr(0,3) == 'obd') {
			element.style.display = 'block';
		}
		else {
			element.style.display = 'none';
		}
	}
	if (element.style.display == 'none') {
		element.style.display = 'block';
	}
	else{
		element.style.display = 'none';
	}
}

function toggle_plusminus(element) {
	//element = document.getElementById(id);
	if (element.innerHTML == '+') {
		element.innerHTML = '-';
		
	}  
	else {
		element.innerHTML = '+';
	}

}


var PANEL_NORMAL_CLASS    = "defineframe";
var PANEL_COLLAPSED_CLASS = "defineframe hidden";
var PANEL_ANIMATION_DELAY = 20; /*ms*/
var PANEL_ANIMATION_STEPS = 20;

function animateTogglePanel(panelContent)
{
	if (panelContent.className ==  PANEL_NORMAL_CLASS) {
	 	expanding = false;
	}       
	else {
	 	expanding = true;
	}
	
	// make sure the content is visible before getting its height
	panelContent.style.display = "block";
	if (PANEL_NORMAL_CLASS == "") { // is a big box, must hide text
		panelContent.className = PANEL_COLLAPSED_CLASS;
	}
	else { // small box, display text
	  panelContent.className = PANEL_NORMAL_CLASS;
	}
	
	
	// get the height of the content
	var contentHeight = panelContent.offsetHeight;
	
	// if panel is collapsed and expanding, we must start with 0 height
	if (expanding)
		panelContent.style.height = "0px";
	
	var stepHeight = (contentHeight) / PANEL_ANIMATION_STEPS;
	var direction = (!expanding ? -1 : 1);
	
	setTimeout(function(){animateStep(panelContent,1,stepHeight,direction)}, PANEL_ANIMATION_DELAY);
}



function animateStep(panelContent, iteration, stepHeight, direction)
{
	if (iteration<PANEL_ANIMATION_STEPS)
	{
		panelContent.style.height = Math.round(((direction>0) ? iteration : PANEL_ANIMATION_STEPS - iteration) * stepHeight) +"px";
		iteration++;
		setTimeout(function(){animateStep(panelContent,iteration,stepHeight,direction)}, PANEL_ANIMATION_DELAY);
		//alert("step")
	}
	else
	{
		// set class for the panel
		panelContent.className = (direction<0) ? PANEL_COLLAPSED_CLASS : PANEL_NORMAL_CLASS;
		// clear inline styles
		panelContent.style.display = panelContent.style.height = "";
		
	}
}

function open_or_close(header) {
	//alert(header.innerHTML);
	//alert(header.parentNode.innerHTML);
	//alert(header.parentNode.children[1].innerHTML);
 	//toggle_display(header.parentNode.children[1]);
 	PANEL_NORMAL_CLASS    = "defineframe";
   PANEL_COLLAPSED_CLASS = "defineframe hidden";
 	animateTogglePanel(header.parentNode.children[1],function(){});
 	toggle_plusminus(header.children[0]);
}



function minimize_active_subcorpus(){ 
	var element = document.getElementById('subcorpus' + active_subcorpus);
	
	if (element != null) {
	 	PANEL_NORMAL_CLASS    = "";
      PANEL_COLLAPSED_CLASS = "hidden";
      //alert("here")
 	   animateTogglePanel(element.children[1]);
 	   //element.children[1].style.display = 'none';
		//element.children[0].className == "";
		//element.className = 'finishedcorpus';
		setTimeout(function(){finish_minimize(element)}, PANEL_ANIMATION_DELAY*PANEL_ANIMATION_STEPS);

		//alert("there")
//
		//
	}
}

function finish_minimize(element) {    
	element.children[1].style.display = 'none';
	element.children[0].children[0].innerHTML = element.children[0].children[0].innerHTML.substr(7,element.children[0].children[0].innerHTML.length);	
	element.children[0].className = "";
	element.className = 'finishedcorpus';
}


function add_subcorpus() {
	if (subcorpus_count == 9) {
	 	alert("Max number of subcorpora reached!");
	}   
	else
	{
		if (active_subcorpus != 0) {
			minimize_active_subcorpus();
		
		}
		minimize("analyzeoptions");
		minimize("analyzeend");
		minimize("exportoptions");
		minimize("exportend");
		element = document.getElementById('subcorpustemplate');
		new_element = element.cloneNode(true); 
		subcorpus_count += 1;
		new_element.id = 'subcorpus' + subcorpus_count.toString();
		new_element.children[0].children[0].innerHTML = 'Define Subcorpus ' + subcorpus_count.toString(); 
		subcorpus_div = document.getElementById('subcorpora');
		if (active_subcorpus != -1) {
			connector = document.getElementById('start');
			new_connector = connector.cloneNode(true);
			subcorpus_div.appendChild(new_connector);
		}
		subcorpus_div.appendChild(new_element);
		active_subcorpus = subcorpus_count;
	}
}

function activate_subcorpus_function(element) {
	minimize_active_subcorpus();
	minimize("analyzeoptions");
	minimize("analyzeend");
	minimize("exportoptions");
	minimize("exportend");
	element.className='activesubcorpus';  
	element.children[0].className = 'corpusheader';
	element.children[0].children[0].innerHTML = 'Define ' + element.children[0].children[0].innerHTML;
	active_subcorpus = parseInt(element.id.substr(element.id.length - 1));	
	PANEL_NORMAL_CLASS    = "";
   PANEL_COLLAPSED_CLASS = "hidden";	
	animateTogglePanel(element.children[1]);

}

function finish_maximize(element) {

}


function toggle_active(subcorpus_header) {
	active_subcorpus_element = document.getElementById('subcorpus' + active_subcorpus);
	if (active_subcorpus_element != subcorpus_header.parentNode) {
		 activate_subcorpus_function(subcorpus_header.parentNode);
	}
}


function minimize(id) {
  element = document.getElementById(id);
  if (element.className != 'hidden') {
  	element.className = 'hidden'; 
  }
  
}

function activate(id) {
	element = document.getElementById(id);
	element.className = '';

}

function activate_export() {
	minimize_active_subcorpus();
	active_subcorpus = 0;
	minimize("analyzeoptions");
	minimize("analyzeend");	
	activate("exportoptions");
	activate("exportend");
	if (fork_clicked == 'none') {
		var export_button = document.getElementById('exportbutton');
		export_button.style.right = "0px";
		export_button.style['z-index'] = 500;
		var add_subcorpus_button = document.getElementById('addsubcorpus');
		add_subcorpus_button.style.right = "160px";

		
	}
	else {
	 if (fork_clicked == 'analyze') {
		var export_button = document.getElementById('exportbutton');
		export_button.style.right = "0px";	
		export_button.style.background = "#fff"	
		var add_subcorpus_button = document.getElementById('addsubcorpus');
		add_subcorpus_button.style.right = "160px";	
		var analyze_button = document.getElementById('analyzebutton');
		analyze_button.style.right = "-160px";	 
	 	}
	
		} 
		var analyze_button = document.getElementById('analyzebutton');
		analyze_button.style.background = "#dcdada";
		var decision_image = document.getElementById('decisionforkimage');
		decision_image.src = "../images/selectexport.png";
		var line_to_add_sub = document.getElementById('linetoaddsubcorpus');
		line_to_add_sub.className = 'invisible';
		fork_clicked = 'export';

}

function activate_analyze() {
	minimize_active_subcorpus();
	active_subcorpus = 0;
	minimize("exportoptions");
	minimize("exportend");	
	activate("analyzeoptions");
	activate("analyzeend");  
	
	if (fork_clicked == 'none') {
		var analyze_button = document.getElementById('analyzebutton');
		analyze_button.style.right = "0px";
		analyze_button.style['z-index'] = 500;
		var add_subcorpus_button = document.getElementById('addsubcorpus');
		add_subcorpus_button.style.right = "-160px";
		
	}
	else {
		if (fork_clicked == 'export') {
			var export_button = document.getElementById('exportbutton');
			export_button.style.right = "160px";		
			var add_subcorpus_button = document.getElementById('addsubcorpus');
			add_subcorpus_button.style.right = "-160px";	
			var analyze_button = document.getElementById('analyzebutton');
			analyze_button.style.right = "0px";
			analyze_button.style.background = "#fff"	
		
		}
		}
		var export_button = document.getElementById('exportbutton');
		export_button.style.background = "#dcdada";
		var decision_image = document.getElementById('decisionforkimage');
		decision_image.src = "../images/selectanalyze.png";
		var line_to_add_sub = document.getElementById('linetoaddsubcorpus');
		line_to_add_sub.className = 'invisible';
		fork_clicked = 'analyze';


}

function update_check_boxes(form_element){
	var theform = form_element.form;

	
	 value = form_element.options[form_element.selectedIndex].value;
	 switch (value) {
		case "1":
			theform.elements['front'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['front'].checked = true;
			theform.elements['docTitle'].checked = true;
			theform.elements['div:preface'].checked = true;
			theform.elements['contents'].checked = true;
			theform.elements['div:introduction'].checked = true;
			theform.elements['body'].checked = true;
			theform.elements['head'].checked = true;
			theform.elements['back'].checked = true;
			theform.elements['afterword'].checked = true;
			theform.elements['note'].checked = true;
			break;
		case "2":
			theform.elements['front'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['front'].checked = false;
			theform.elements['docTitle'].checked = false;
			theform.elements['div:preface'].checked = true;
			theform.elements['contents'].checked = false;
			theform.elements['div:introduction'].checked = true;
			theform.elements['body'].checked = true;
			theform.elements['head'].checked = false;
			theform.elements['back'].checked = false;
			theform.elements['afterword'].checked = true;
			theform.elements['note'].checked = false;
			break;
			
		case "3":
			theform.elements['front'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['front'].checked = false;
			theform.elements['docTitle'].checked = false;
			theform.elements['div:preface'].checked = false;
			theform.elements['contents'].checked = false;
			theform.elements['div:introduction'].checked = false;
			theform.elements['body'].checked = true;
			theform.elements['head'].checked = false;
			theform.elements['back'].checked = false;
			theform.elements['afterword'].checked = false;
			theform.elements['note'].checked = false;
			break;
			
		case "4": 
			theform.elements['p|prose'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['p|prose'].checked = true;
			theform.elements['said'].checked = true;
			theform.elements['div:prologue'].checked = true;
			theform.elements['div:epilogue|prose'].checked = true;
			break;


		case "5":
			theform.elements['p|prose'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['p|prose'].checked = false;
			theform.elements['said'].checked = true;
			theform.elements['div:prologue'].checked = false;
			theform.elements['div:epilogue|prose'].checked = false;
			break;		
	

		case "6":
			theform.elements['p|prose'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['p|prose'].checked = true;
			theform.elements['said'].checked = false;
			theform.elements['div:prologue'].checked = true;
			theform.elements['div:epilogue|prose'].checked = true; 
			break;
			
		case "7":
			theform.elements['lg|poetry'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			theform.elements['lg|poetry'].checked = true;
			theform.elements['p|poetry'].checked = true;
			break;
			
		
		case "8":	
			theform.elements['lg|poetry'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";		
			theform.elements['lg|poetry'].checked = true;
			theform.elements['p|poetry'].checked = false;
			break;                             
			
	   case "9":
	   	theform.elements['castList'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
	   	theform.elements['castList'].checked = true;
	   	theform.elements['speaker'].checked = true;
	   	theform.elements['set'].checked = true;
	   	theform.elements['stage'].checked = true;
	   	theform.elements['p|play'].checked = true;
	   	theform.elements['lg|play'].checked = true;
	   	theform.elements['div:epilogue|play'].checked = true;
	   	break;
	   	
	   case "10":
	   	theform.elements['castList'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
	   	theform.elements['castList'].checked = false;
	   	theform.elements['speaker'].checked = false;
	   	theform.elements['set'].checked = false;
	   	theform.elements['stage'].checked = false;
	   	theform.elements['p|play'].checked = true;
	   	theform.elements['lg|play'].checked = true;
	   	theform.elements['div:epilogue|play'].checked = false;
	   	break;	   	


	   case "11":
	   	theform.elements['castList'].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
	   	theform.elements['castList'].checked = false;
	   	theform.elements['speaker'].checked = false;
	   	theform.elements['set'].checked = true;
	   	theform.elements['stage'].checked = true;
	   	theform.elements['p|play'].checked = false;
	   	theform.elements['lg|play'].checked = false;
	   	theform.elements['div:epilogue|play'].checked = false;
	   	break;	

		}     
}

function toggle_prose_macro(theform) {
	if (!theform.elements['fiction'].checked && !theform.elements['nonfiction'].checked) {
	 	theform.elements['prose_macro'].parentNode.parentNode.className = "withintext hidden";
	}
	else {
		theform.elements['prose_macro'].parentNode.parentNode.className = "withintext";
	}
	
	if (theform.elements['fiction'].checked) {
		document.getElementById('person_row').style = "" 
		document.getElementById('NER_row').style = "" 
	}
	else {
		document.getElementById('person_row').style = "display:none;"
		document.getElementById('NER_row').style = "display:none;"	
	}
}

function toggle_drama_macro(theform) {
	if (theform.elements['play'].checked) {
	theform.elements['drama_macro'].parentNode.parentNode.className = "withintext";
	 	
	}
	else {
	theform.elements['drama_macro'].parentNode.parentNode.className = "withintext hidden";
	}

}

function toggle_poetry_macro(theform) {
	if (theform.elements['poetry'].checked) {
	theform.elements['poetry_macro'].parentNode.parentNode.className = "withintext";
	 	
	}
	else {
	theform.elements['poetry_macro'].parentNode.parentNode.className = "withintext hidden";
	}

}

function toggle_all_genres(theform) {
if (theform.elements['all'].checked) {
	theform.elements['poetry'].checked = true;
   theform.elements['fiction'].checked = true;
   theform.elements['nonfiction'].checked = true;
   theform.elements['play'].checked = true;  
   theform.elements['periodical'].checked = true;
   toggle_poetry_macro(theform);
   toggle_drama_macro(theform);
   toggle_prose_macro(theform);
   }
else {
	theform.elements['poetry'].checked = false;
   theform.elements['fiction'].checked = false;
   theform.elements['nonfiction'].checked = false;
   theform.elements['play'].checked = false;  
   theform.elements['periodical'].checked = false;
   toggle_poetry_macro(theform);
   toggle_drama_macro(theform);
   toggle_prose_macro(theform);

}
   
}

function add_lexical_filter(add_button) {
	var num = parseInt(add_button.getAttribute('data'));
	var table = add_button.parentNode.children[0];
	new_row = document.getElementById('lexicalfiltertemplate').cloneNode(true);
	new_row.id == '';
	table.appendChild(new_row);    
	num += 1;
	new_row.children[1].children[0].name = 'lexicalfilter' + num;
	add_button.setAttribute('data',num.toString());
	
	
}

function add_lexical_tag(type) {
	add_button = document.getElementById(type+'lexiconaddbutton');
	var num = parseInt(add_button.getAttribute('data'));
	var table = add_button.parentNode.children[1];
	new_row = document.getElementById('lexicaltagtemplate').cloneNode(true);
	table.appendChild(new_row);    
	num += 1;
	new_row.id = 'lexicaltagrow' + num;
	new_row.children[0].children[0].name = new_row.children[0].children[0].name + "-" + num;
	for (i=0;i < 3;i++) {
	 	new_row.children[1].children[i].name = new_row.children[1].children[i].name + "-" + num;
	}
	add_button.setAttribute('data',num.toString());
	return new_row;
	
}

function add_measure() {
	add_button = document.getElementById('measureaddbutton');
	var num = parseInt(add_button.getAttribute('data'));
	var table = add_button.parentNode.children[0];
	new_row = document.getElementById('measuretemplate').cloneNode(true);
	table.appendChild(new_row);    
	num += 1;
	new_row.id = 'measurerow' + num;
	new_row.children[0].children[0].name = new_row.children[0].children[0].name + "-" + num;
	//for (i=0;i < 3;i++) {
	// 	new_row.children[1].children[i].name = new_row.children[1].children[i].name + "-" + num;
	//}
	add_button.setAttribute('data',num.toString());
	return new_row;
	
}


function remove_all_lexical_tags(type) {
	add_button = document.getElementById(type+'lexiconaddbutton');
	add_button.setAttribute('data','0');
	var i = 1;
	table = document.getElementById(type+'lexicontable')
	while (table.children.length > 0) {
		 	table.removeChild(table.children[0]);
		 }
}

function remove_all_measures() {
	add_button = document.getElementById('measureaddbutton');
	add_button.setAttribute('data','0');
	var i = 1;
	table = document.getElementById('measuretable')
	while (table.children.length > 0) {
		 	table.removeChild(table.children[0]);
		 }
}


function reveal_sublexicon(main_tag) {
	 var num = parseInt(main_tag.name.split("-")[1]);
	 main_tag.form["GIlexicaltag-" +num].className = 'hidden';
	 main_tag.form["MRClexicaltag-" +num].className = 'hidden';	
	 main_tag.form["sixstylepluslexicaltag-" +num].className = 'hidden';	
	 try {
	 	main_tag.form[main_tag.options[main_tag.selectedIndex].value + 'lexicaltag-' + num].className = '';
	 }
	 catch (err) {}
}
                
function start_up() {
	add_subcorpus();
	add_lexical_tag('export');
	add_lexical_tag('analyze');
	add_measure();
	/*
	var fileSelector = document.createElement('input');
 	fileSelector.setAttribute('type', 'file');

 	document.getElementById('save1').onclick = function () {
      fileSelector.click();
      return false;
   }
      
   document.getElementById('save2').onclick = function () {
      fileSelector.click();
      return false;
 	}
 	*/
}

function get_subcorpus_info(data) {     

	subcorpus_num = 1;

	subcorpus_div = document.getElementById("subcorpus" + subcorpus_num)
	
	while (subcorpus_div != null)
	{
		thisform = subcorpus_div.children[1];
		var text_restriction = {};
	 	var genres = [];
	 	var arr = ["fiction","nonfiction","play","poetry","periodical"];
	 	for (var i = 0; i < arr.length; i++) {
	    if (thisform.elements[arr[i]].checked) {
	     genres.push(arr[i]);
	    }
		}
		text_restriction["Genre"] = genres;
		
		if (thisform.elements['author_name'].value) {
			text_restriction["Author"] = thisform.elements['author_name'].value;
			
		}  
		
		if (thisform.elements['author_list'].options[thisform.elements['author_list'].selectedIndex].value != "None") {
			text_restriction["author_list"] = "Author|"+thisform.elements['author_list'].options[thisform.elements['author_list'].selectedIndex].value
		}
		
	   if (thisform.elements['gender'].value != "both") {
	   	text_restriction["Author Gender"] = thisform.elements['gender'].value;
	   }
	   	
	   	
		if (thisform.elements['author_birth_start'].value && thisform.elements['author_birth_end'].value)
		{
			var birth_range = [];
			birth_range.push(parseInt(thisform.elements['author_birth_start'].value));
			birth_range.push(parseInt(thisform.elements['author_birth_end'].value));
			text_restriction["Author Birth"] = birth_range;
		}
		
		if (thisform.elements['author_death_start'].value && thisform.elements['author_death_end'].value)
		{
			var death_range = [];
			death_range.push(parseInt(thisform.elements['author_death_start'].value));
			death_range.push(parseInt(thisform.elements['author_death_end'].value));
			text_restriction["Author Death"] = death_range;
		}


		if (thisform.elements['nationality'].value != 'Any') {
			text_restriction["Author Nationality"] = thisform.elements['nationality'].value;
			
		}  

	if (thisform.elements['text_title'].value) {
			text_restriction["Title"] = thisform.elements['text_title'].value;
			
		}  
		
		if (thisform.elements['title_list'].options[thisform.elements['title_list'].selectedIndex].value != "None") {
			text_restriction["title_list"] = "Title|"+thisform.elements['title_list'].options[thisform.elements['title_list'].selectedIndex].value
		}
		
		
		if (thisform.elements['lang'].value) {
			text_restriction["Language"] = thisform.elements['lang'].value;
			
		}  
		
		if (thisform.elements['publication_date_start'].value && thisform.elements['publication_date_end'].value)
		{
			var publication_range = [];
			publication_range.push(parseInt(thisform.elements['publication_date_start'].value));
			publication_range.push(parseInt(thisform.elements['publication_date_end'].value));
			text_restriction["Publication Date"] = publication_range;
		}
		
		
		if (thisform.elements['publication_country'].options[thisform.elements['publication_country'].selectedIndex].value != "Any") {
			text_restriction["Publication Country"] = thisform.elements['publication_country'].options[thisform.elements['publication_country'].selectedIndex].value
		}	
		

		if (thisform.elements['LoC_class'].options[thisform.elements['LoC_class'].selectedIndex].value != "No Restrictions") {
			text_restriction["LoC Class"] = thisform.elements['LoC_class'].options[thisform.elements['LoC_class'].selectedIndex].value
		}	


		if (thisform.elements['LoC_subject'].value) {
			text_restriction["Subject"] = thisform.elements['LoC_subject'].value;
			
		}  
		
		if (thisform.elements['collection'].value != "both") {
	   	text_restriction["Collection"] = thisform.elements['collection'].value;
	   }
		
	   if (thisform.elements['person'].value != "both") {
	   	text_restriction["Person"] = thisform.elements['person'].value;
	   }
		
		text_restriction["wanted_tags"] = [];
		text_restriction["not_wanted_tags"] = [];
		
		var struct_tags = ["front","docTitle","div:preface","contents","div:introduction","body","head","back","afterword","note","said","div:prologue","div:epilogue|play","div:epilogue|prose" ,"lg|poetry", "lg|play","castList","speaker","set","stage","p|play","p|poetry","p|prose"];
		
		for (var i = 0; i < struct_tags.length; i++) {
	   	if (thisform.elements[struct_tags[i]].checked) {
	     		text_restriction["wanted_tags"].push(struct_tags[i]); 
	    }                       
	    	else { 
	    		text_restriction["not_wanted_tags"].push(struct_tags[i]); 	
	    	}
		}
	    	
	    text_restriction["lexical_restrictions"] = [];
	   lexnum = 1
	    
	   while ( ('lexicalfilter' + lexnum) in thisform.elements ) {
			var maintag = thisform.elements['lexicalfilter' + lexnum];
			if (maintag.value) {
				text_restriction["lexical_restrictions"].push(maintag.value);
			} 
			lexnum++;
			
		 }                               
		 
		 
		 
		data["subcorpus"+ subcorpus_num + "_restrictions"] = text_restriction;
		subcorpus_num++;
		subcorpus_div = document.getElementById("subcorpus" + subcorpus_num);
	}
	data["num_subcorpora"] = subcorpus_num - 1;
}

function get_measures(thisform,measure_dict) {
	num = 1;
	while (('measuremain-' + num) in thisform.elements) {
		var maintag = thisform.elements['measuremain-' + num];
		var value = maintag.options[maintag.selectedIndex].value;
		measure_dict.push(value);
		num++;
	}
}

function get_lexical_tags(thisform,lexical_tag_dict, for_analysis_dict) {
	lexnum = 1;
	while (('lexicaltagmain-' + lexnum) in thisform.elements) {
		var maintag = thisform.elements['lexicaltagmain-' + lexnum];
		var value = maintag.options[maintag.selectedIndex].value;
	   if (value != 'none') {
	   	if (value == 'GI' || value == 'MRC' || value== 'sixstyleplus') {
	   		value2 = thisform.elements[value+ 'lexicaltag-' + lexnum].options[thisform.elements[value+ 'lexicaltag-' + lexnum].selectedIndex].value;
	   		if (value == 'sixstyleplus') {
	   		    lemmatize = "notlem";
	   		    }
	   		else {
	   				lemmatize = "lem";
	   			}
	   		lexical_tag_dict.push(value + "|" + value2 + "|notcasesens|" + lemmatize);
	   		if (for_analysis_dict != null) {
	   			for_analysis_dict.push(value2)
	   		}
	   	}
	   	else {
	   		if (for_analysis_dict != null) {
	   			for_analysis_dict.push(value)
	   		}
	   		lexical_tag_dict.push("user_lexicon|" + value + "|notcasesen|lem");
	   	  
	   	} 
	   }	
	 	lexnum++;  	
	
	}
}

/*
function query_server(data) {

 	//alert(JSON.stringify(data));
 	var xmlHttpRqst = CreateXmlHttpObject( );
 	options = encodeURIComponent(JSON.stringify(data));
 	
 	xmlHttpRqst.open( "RUN", options, false );
	try {
		xmlHttpRqst.send( null );
	}
	catch(err)
	{
		alert(err);
	}

}
*/

function query_server(data) {

	var f = document.createElement("form");
	f.setAttribute('method',"get");
	//f.setAttribute('action',"results_page.py");
	f.setAttribute('action',"results_page.cgi");
	f.setAttribute('display','none');
	var i = document.createElement("input");
	i.setAttribute('value', JSON.stringify(data));
	i.setAttribute('name', "data");
	f.appendChild(i);
	var i = document.createElement("button");  // for firefox compatibility
	i.setAttribute('type',"submit");
	f.appendChild(i);
	document.body.appendChild(f)
	f.submit();
}

function selectElement(selection,value) {
     for(var i=0;i<selection.options.length;i++){
            if (selection.options[i].innerHTML == value || selection.options[i].value == value) {
                selection.selectedIndex = i;
                break;
            }
        }
}

function query_server_for_saved_parameters(filename) {
	//alert("try");
 	var xmlHttpRqst = CreateXmlHttpObject( );

 	
 	xmlHttpRqst.open( "GET", "load_parameters.cgi?filename=" + filename, false ); 
	try {
		xmlHttpRqst.send( null );
	}
	catch(err)
	{
		alert(err);
	}
	
	response = xmlHttpRqst.responseText
	if (response) {
		params = JSON.parse(response);
	}
	else {
		params = false;
	}         
	return params;
}

function query_server_check_corpus_path(filename) {
	//alert("try");
 	var xmlHttpRqst = CreateXmlHttpObject( );

 	
 	xmlHttpRqst.open( "GET", "check_corpus_path.cgi?path=" + document.getElementById("path").value, false ); 
	try {
		xmlHttpRqst.send( null );
	}
	catch(err)
	{
		alert(err);
	}
	
	response = xmlHttpRqst.responseText;
	document.getElementById("result").innerHTML = response;
}

function load_parameters() {
	selector = document.getElementById('loadfilename')
	filename = selector.options[selector.selectedIndex].value;
	if (filename != "<None>") {
		data = query_server_for_saved_parameters(filename)
		for (var i = 1; i <= data["num_subcorpora"]; i++) {
			if (i > subcorpus_count) {
			 	add_subcorpus();
			}
			
			
			restrictions = data["subcorpus" + i + "_restrictions"]

			subcorpus_div = document.getElementById("subcorpus" + i)
		
			thisform = subcorpus_div.children[1];
	
		 	var arr = ["fiction","nonfiction","play","poetry","periodical"];
		 	for (var j  = 0; j < arr.length; j++) {
		     thisform.elements[arr[j]].checked = false;
		    }
		    
		 	for (var j  = 0; j < restrictions['Genre'].length; j++) {
		 		thisform.elements[restrictions['Genre'][j]].click();
		 	}
			
			if ('Author' in restrictions) {
				thisform.elements['author_name'].value = restrictions['Author'];
				
			} 
			else {
				thisform.elements['author_name'].value = "";
			}
			
			if ('author_list' in restrictions) {
			 	selectElement(thisform.elements['author_list'],restrictions['author_list'].split("|")[1]);
			}
			else {
			 	selectElement(thisform.elements['author_list'],"None");
			}
			
			if ('Author Gender' in restrictions) {
			   if (restrictions['Author Gender'] == 'M') {
			   	thisform.elements['gender'][1].checked = true;
			   }
			   else {
			   	thisform.elements['gender'][2].checked = true; 
			  }
			}
			else {
				thisform.elements['gender'][0].checked = true;
			}
			
			if ("Author Birth" in restrictions) {
			 thisform.elements['author_birth_start'].value = restrictions["Author Birth"][0].toString();
			 thisform.elements['author_birth_end'].value = restrictions["Author Birth"][1].toString();			
			
			}
			else {
			 thisform.elements['author_birth_start'].value = "";
			 thisform.elements['author_birth_end'].value = "";
			}
		   	
			if ("Author Death" in restrictions) {
			 thisform.elements['author_death_start'].value = restrictions["Author Death"][0].toString();
			 thisform.elements['author_death_end'].value = restrictions["Author Death"][1].toString();			
			
			}
			else {
			 thisform.elements['author_death_start'].value = "";
			 thisform.elements['author_death_end'].value = "";
			}
			
			if ('Author Nationality' in restrictions) {
			 	selectElement(thisform.elements['nationality'],restrictions['Author Nationality']);
			}
			else {
			 	selectElement(thisform.elements['nationality'],"Any");
			}

			if ("Title" in restrictions) {
				thisform.elements['text_title'].value = restrictions["Title"]
			}
			else {
				thisform.elements['text_title'].value = ""
			}

			if ('title_list' in restrictions) {
			 	selectElement(thisform.elements['title_list'],restrictions['title_list'].split("|")[1]);
			}
			else {
			 	selectElement(thisform.elements['title_list'],"None");
			}


			if ('Language' in restrictions) {
			 	selectElement(thisform.elements['lang'],restrictions['Language']);
			}
			else {
			 	selectElement(thisform.elements['lang'],"English");
			}
			
			
			if ("Publication Date" in restrictions) {
			 thisform.elements['publication_date_start'].value = restrictions["Publication Date"][0].toString();
			 thisform.elements['publication_date_end'].value = restrictions["Publication Date"][1].toString();			
			
			}
			else {
			 thisform.elements['publication_date_start'].value = "";
			 thisform.elements['publication_date_end'].value = "";
			}
			
			
			if ('Publication Country' in restrictions) {
			 	selectElement(thisform.elements['publication_country'],restrictions['Publication Country']);
			}
			else {
			 	selectElement(thisform.elements['publication_country'],"Any");
			}
			
			
			if ('LoC Class' in restrictions) {
			 	selectElement(thisform.elements['LoC_class'],restrictions['LoC Class']);
			}
			else {
			 	selectElement(thisform.elements['LoC_class'],"No Restrictions");
			}
		
			if ('Subject' in restrictions) {
				thisform.elements['LoC_subject'].value = restrictions['Subject']
			}
			else {
				thisform.elements['LoC_subject'].value = ""
			}


			if ('Collection' in restrictions) {
			   if (restrictions['Collection'] == 'collection') {
			   	thisform.elements['collection'][2].checked = true;
			   }
			   else {
			   	thisform.elements['collection'][1].checked = true; 
			  }
			}
			else {
				thisform.elements['collection'][0].checked = true;
			}
			
			
			if ('Person' in restrictions) {
			   if (restrictions['Person'] == '1st') {
			   	thisform.elements['person'][2].checked = true;
			   }
			   else {
			   	thisform.elements['person'][1].checked = true; 
			  }
			}
			else {
				thisform.elements['person'][0].checked = true;
			}

			for (var j = 0; j < restrictions["wanted_tags"].length; j++) {
				thisform.elements[restrictions["wanted_tags"][j]].checked = true;
			} 
			
			for (var j = 0; j < restrictions["not_wanted_tags"].length; j++) {
				thisform.elements[restrictions["not_wanted_tags"][j]].checked = false;
				thisform.elements[restrictions["not_wanted_tags"][j]].parentNode.parentNode.parentNode.parentNode.parentNode.className = "withintextoptions";
			}    
			thisform['lexicalfilter1'].value = "";
		   var j = 2;
			while ('lexicalfilter' + j in thisform) {
			   thisform['lexicalfilter' + j].parentNode.parentNode.parentNode.parentNode.removeChild(thisform['lexicalfilter' + j].parentNode.parentNode.parentNode);
				j+= 1;
			} 
			button = thisform['lexicalfilter1'].parentNode.parentNode.parentNode.parentNode.parentNode.children[1]
			if (restrictions.lexical_restrictions.length > 0) {
				thisform['lexicalfilter1'].value = restrictions.lexical_restrictions[0] 
				
		   	for (var j = 2; j <= restrictions.lexical_restrictions.length; j++) {
		   		add_lexical_filter(button);
		   		thisform['lexicalfilter' + j].value = restrictions.lexical_restrictions[j - 1]; 
		   } 
		    				
		 }  
		 
		 
		if (data['mode'] == 'export') {
			thisform = document.getElementById('export_form');
		
			activate_export();

			thisform.elements['output_dir'].value = data['output_dir'];
		 	if ('maxnum' in data) {
		 		 thisform.elements['maxnum'].value = data['maxnum'].toString();
		 	}
		 	
		 	thisform.elements['randomize_order'].checked = data['randomize_order'];
		 	
		 	if (data['tagged']) {
		 		thisform.elements['tagged'][0].checked = true;
		 	}                        
		 	else {
		 		thisform.elements['tagged'][1].checked = true;
		 	}
		 	
		 	if (data['lemma']) {
		 		thisform.elements['lemmatized'][0].checked = true;
		 	}                        
		 	else {
		 		thisform.elements['lemmatized'][1].checked = true;
		 	}
		 	/*
		 	if ('not_display_tags' in data && 'persName' in data['not_display_tags']) {
		 		thisform.elements['persName'][1].checked = true;
		   }
		 	else {
		 	  thisform.elements['persName'][0].checked = true;
		 	} 
		 	*/
		 	
			if (data["output_format"] == "plain") {
				thisform.elements['output_format'][1].click();
			}
			else {
				thisform.elements['output_format'][0].click();
			}
		
			 if (data['persName']) {
		 		thisform.elements['persName'].checked = true;
		 	}                        
		 	else {
		 		thisform.elements['persName'].checked = false;
		 	}	 	
		 	
			 if (data['placeName']) {
		 		thisform.elements['placeName'].checked = true;
		 	}                        
		 	else {
		 		thisform.elements['placeName'].checked = false;
		 	}			 	
		 
		 } 
		 else if  (data['mode'] == 'analyze') {
		 thisform = document.getElementById('analyze_form');
		  activate_analyze();
		  
		  	if ('maxnum' in data) {
		 		 thisform.elements['maxnum'].value = data['maxnum'].toString();
		 	}
		 	if ('randomize_order' in data) {
		 		thisform.elements['randomize_order'].checked = data['randomize_order'];
		 	}

			if ('output_file' in data) {
				thisform.elements['output_file'].value = data['output_file'];
			}
	
		 	//if ('not_display_tags' in data) {
		 	//	thisform.elements['persName'][1].checked = true;
		   //}
		 	//else {
		 	//  thisform.elements['persName'][0].checked = true;
		 	//}
		 	remove_all_measures();
		 	if ('measures' in data) {
			 	for (var j = 1; j <= data['measures'].length; j++) {
			   element = add_measure()                 
			   selectElement(element.children[0].children[0], data['measures'][j-1])
			  }
		  }
		 }
		 remove_all_lexical_tags(data['mode']); 
		 

		 for (var j = 1; j <= data['lexical_tags'].length; j++) {
		  element = add_lexical_tag(data['mode'])                 
		  if (data['lexical_tags'][j-1].lastIndexOf("user_lexicon", 0) === 0) {
		  		selectElement(element.children[0].children[0], data['lexical_tags'][j-1].split("|")[1])
		  }
		  else {
		  		var stuff = data['lexical_tags'][j-1].split("|")
		  		var main_lex = stuff[0]
		  		var sub_lex = stuff[1]
		  		selectElement(element.children[0].children[0], main_lex)
		  		reveal_sublexicon(element.children[0].children[0]);
		  		if (main_lex == "GI") {
		  			selectElement(element.children[1].children[0], sub_lex)
		  		}
		  		else if (main_lex == "MRC") {
		  			selectElement(element.children[1].children[1], sub_lex)
		  		}
		  		else if (main_lex == "sixstyleplus") {
		  			selectElement(element.children[1].children[2], sub_lex)
		  		}
		  }
		  
		 }
	
	}
	
	}
}


function prepare_data_for_analysis() {

 	var data = {};
 	data['mode'] = 'analyze';
 	thisform = document.getElementById('analyze_form');
	data["lexical_tags"] = [];
	data["tags_for_analysis"] = [];
	data["measures"] = [];
	
	
	get_lexical_tags(thisform,data["lexical_tags"],data["tags_for_analysis"]);
	get_measures(thisform,data["measures"]);
	
	
 	data['not_display_tags'] = [];
 	if (thisform.elements['output_file'].value) {	
 		data['output_file'] =thisform.elements['output_file'].value;
 	}
 	if (thisform.elements['maxnum'].value) {
 		data['maxnum'] = parseInt(thisform.elements['maxnum'].value);
 	}
 	
 	data['randomize_order'] = thisform.elements['randomize_order'].checked
	
	get_subcorpus_info(data);

	data["save_filename"] = document.getElementById('savefilename2').value;
	
	return data;
	
	

}



function prepare_data_for_export(){
 	var data = {}
 	thisform = document.getElementById('export_form');
 	data['mode'] = 'export'
 	data['output_dir'] =thisform.elements['output_dir'].value;
 	if (thisform.elements['maxnum'].value) {
 		data['maxnum'] = parseInt(thisform.elements['maxnum'].value);
 	}
 	if (thisform.elements['tagged'].value=="true") {
 		data['tagged'] = true;
 	}                        
 	else {
 		data['tagged'] = false;
 	}
 	
 	 if (thisform.elements['lemmatized'].value=="true") {
 		data['lemma'] = true;
 	}                        
 	else {
 		data['lemma'] = false;
 	}
 	
 	 if (thisform.elements['persName'].checked) {
 		data['persName'] = true;
 	}                        
 	else {
 		data['persName'] = false;
 	}
 	
 	if (thisform.elements['placeName'].checked) {
 		data['placeName'] = true;
 	}                        
 	else {
 		data['placeName'] = false;
 	}
 	data['not_display_tags'] = []
 	/*
 	if (thisform.elements['persName'].value=="false") {
 		data['not_display_tags'] = ['persName']
 	}
 	else {
 		data['not_display_tags'] = []
 	} 
 	*/
 	
	
	data["output_format"] = thisform.elements['output_format'].value;
	data['randomize_order'] = thisform.elements['randomize_order'].checked
	
	data["lexical_tags"] = [];
	
	
	get_lexical_tags(thisform,data["lexical_tags"],null);
	
	get_subcorpus_info(data);
	
	data["save_filename"] = document.getElementById('savefilename1').value;
	
	return data;

}

var bad_char_regex = /[\/\?\*\:\;\{\}\\]/

function do_export() {
	thisform = document.getElementById('export_form');
	if (thisform.elements['output_dir'].value == "" || bad_char_regex.test(thisform.elements['output_dir'].value)) {
		alert("You have entered an invalid export filename/directory")
		return
	} 
	if (bad_char_regex.test(document.getElementById('savefilename1').value)) {
		alert("You have entered an invalid parameter filename")
		return
	}
	
	data = prepare_data_for_export();
	data["id"] = g_id;
	query_server(data);

} 	
 	
function do_analysis() {
	thisform = document.getElementById('analyze_form');
	if (bad_char_regex.test(thisform.elements['output_file'].value)) {
		alert("You have entered an invalid analysis filename");
		return
	} 
	if (bad_char_regex.test(document.getElementById('savefilename2').value)) {
		alert("You have entered an invalid parameter filename");
		return
	}	
	data = prepare_data_for_analysis();
	if (data["tags_for_analysis"].length + data["measures"].length == 0 ) {
		alert("No lexicons or measures selected for analysis!");
		return;
	}
	data["id"] = g_id;
	//alert(JSON.stringify(data));
	query_server(data);

} 	                   

function do_save() {
	if (fork_clicked == 'analyze') {
	 	data = prepare_data_for_analysis();
	}  
	else {
		data = prepare_data_for_export();
	}

}
 	