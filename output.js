var iFrequency = 2000; // expressed in miliseconds
var myInterval = 0;
user_id = -1
bar_progress = 0
text_count = 0
running_lexicon_counts = {}
running_totals = {}


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
		panelContent.style.height = Math.round(((direction>0) ? iteration : 10 - iteration) * stepHeight) +"px";
		iteration++;
		setTimeout(function(){animateStep(panelContent,iteration,stepHeight,direction)}, PANEL_ANIMATION_DELAY);
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
 	animateTogglePanel(header.parentNode.children[1]);
 	toggle_plusminus(header.children[0]);
}

function add_one_to_count(subcorpus_num) {
	count_element = document.getElementById("resultcount" + subcorpus_num);
	new_count = parseInt(count_element.innerHTML);
	new_count++;
	count_element.innerHTML = new_count.toString();
	text_count += 1
}
function add_title_and_author (title,author,subcorpus_num) {
	p = document.createElement('p');	
	//p.appendChild(document.createTextNode(author + ",<em>" + title + "</em>"))
	p.innerHTML = author + ", <em>" + title + "</em>"
	document.getElementById("subdefine" + subcorpus_num).appendChild(p);
}

function add_full_text(title,author,subcorpus_num,text) {
	blank_div = document.createElement('div');
	header = document.createElement('div');
	header.setAttribute('onclick','open_or_close(this);')
	header.className = 'subdefineheader'
	toggle =  document.createElement('div');
	toggle.className = 'toggler';
	toggle.appendChild(document.createTextNode('+'));
	

	p = document.createElement('p');	
	//p.appendChild(document.createTextNode(author + ",<em>" + title + "</em>"))
	p.innerHTML = 	author + ", <em>" + title + "</em>"
	header.appendChild(toggle);
	header.appendChild(p);
	text_body = document.createElement('div');
	text_body.className = 'defineframe hidden';
	baby = document.createElement('div');
	baby.className = 'defineframebaby'
	baby.appendChild(document.createTextNode(text));
	baby.innerHTML= baby.innerHTML.replace(/\n/g, '<br />');
	text_body.appendChild(baby);
	subcorpus_div = document.getElementById("subdefine" + subcorpus_num)
	blank_div.appendChild(header);
	blank_div.appendChild(text_body);
	subcorpus_div.appendChild(blank_div);	
} 

function isEmpty(obj) {
    for(var prop in obj) {
        return false;
    }
    return true;
}

function add_to_current_analysis_and_update(analysis_results, token_count, subcorpus) {
	//alert('adding to');
	if (!(subcorpus in running_lexicon_counts)) {
	 	running_lexicon_counts[subcorpus] = {}
		running_totals[subcorpus] = 0
	}
	for (var lexicon in analysis_results) {
		//alert("adding to running_counts")
		if (!(lexicon in running_lexicon_counts[subcorpus])) {
		 	running_lexicon_counts[subcorpus][lexicon] = 0
		} 
		for (j= 0; j < analysis_results[lexicon].length; j++) {
			//alert("add one")
			running_lexicon_counts[subcorpus][lexicon] += analysis_results[lexicon][j]
		} 
	}
	//alert("done")
		
	box = document.getElementById("subdefine" + subcorpus)
	if (box.children.length == 0) {
		for (var lexicon in running_lexicon_counts[subcorpus])  {
			//alert("adding p")
		 	p = document.createElement('p');
		 	box.appendChild(p);
		}
	}
	running_totals[subcorpus] +=token_count
	count = 0
	for (var lexicon in running_lexicon_counts[subcorpus]) {
		//alert("filling p")	
		//alert(running_lexicon_counts[subcorpus][lexicon])
		//alert(running_totals[subcorpus])
		box.children[count].innerHTML = lexicon + ": " + running_lexicon_counts[subcorpus][lexicon]/running_totals[subcorpus]
		count += 1
	}
}

function update_status_bar(tag_dict) {      
	var count = 0;
	//alert("update");
	//alert(text_count);
	//alert(tag_dict["maxnum"]);
	//alert(tag_dict["progress"]);
	//alert(tag_dict["total_texts"]);
	
	percent_of_maxnum = text_count/tag_dict["maxnum"];
	percent_of_corpus = tag_dict["progress"]/tag_dict["total_texts"]
	if (percent_of_maxnum > percent_of_corpus) {
		progress = percent_of_maxnum;
	}
	else {
		progress = percent_of_corpus;
	}
	//alert(progress);
	if (progress > bar_progress) {
		bar_progress = progress;
		//alert(progress);
		document.getElementById("progress").style['width'] = Math.floor(bar_progress*100) + "%";
	}
	
	

}
	


function query_server_for_progress() {
	//alert("try");
 	var xmlHttpRqst = CreateXmlHttpObject( );

 	
 	//xmlHttpRqst.open( "GET", "get_results.py?id=" + user_id, false );
 	xmlHttpRqst.open( "GET", "get_results.cgi?id=" + user_id, false ); 
 	//xmlHttpRqst.open( "GET", "get_results.cgi", false );
	try {
		xmlHttpRqst.send( null );
	}
	catch(err)
	{
		alert(err);
	}
	
	response = xmlHttpRqst.responseText
	//alert("got response")
	//alert(response.length)
	if (response) {
		//alert(response);
		//alert("before parse")
		results = JSON.parse(response);
		//alert(results)
		//alert(results.length)
		if (results.length > 0) {
		   //alert("okay")
			for (i=0;i < results.length;i++) {
				//alert(i);
				curr_result = results[i];
				if ('done' in curr_result) {
					//alert("found_done")
					stop();
					break;
				}
				else {	
				if ('notactive' in curr_result){
					update_status_bar(curr_result);
				}
				else {
				     if ('analysis_results' in curr_result) {
				     //alert('in analysis  section')
					add_one_to_count(curr_result['subcorpus'])

					update_status_bar(curr_result);
					add_to_current_analysis_and_update(curr_result['analysis_results'], curr_result['token_count'], curr_result['subcorpus']);
					
					}
					

					else {
 
						//alert(i);
						//alert("here!!!!!!!!!!!")
						add_one_to_count(curr_result['subcorpus']);
						update_status_bar(curr_result);
						if (curr_result['Author'].length == 0) {
							author = 'Various'
						}
						else {
							author = curr_result['Author'][0]
						}
						if ('text' in curr_result) {
							add_full_text(curr_result['Title'][0],author,curr_result['subcorpus'],curr_result['text'])
						}
						else {
							add_title_and_author(curr_result['Title'][0],author,curr_result['subcorpus'])
						}
				//alert(i);
						}
				}
		}
	}
}
}}


function start() {
	 user_id = document.getElementById("user_id").getAttribute("data")
    myInterval = setInterval( "query_server_for_progress();", iFrequency );  // run
}


function stop() {
	clearInterval(myInterval);  // sto 
	document.getElementById('statusscreen').className = 'hidden';
	document.getElementById('statusbar').className = 'hidden';   
	
}