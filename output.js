var iFrequency = 2000; // expressed in miliseconds
var myInterval = 0;
user_id = -1
bar_progress = 0
text_count = 0
running_lexicon_counts = {}
running_totals = {}
zip_filename = ""
query_count = 0

is_safari = /Version\/[\d\.]+.*Safari/.test(navigator.userAgent)


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


/* FileSaver.js
 * A saveAs() FileSaver implementation.
 * 1.1.20151003
 *
 * By Eli Grey, http://eligrey.com
 * License: MIT
 *   See https://github.com/eligrey/FileSaver.js/blob/master/LICENSE.md
 */

/*global self */
/*jslint bitwise: true, indent: 4, laxbreak: true, laxcomma: true, smarttabs: true, plusplus: true */

/*! @source http://purl.eligrey.com/github/FileSaver.js/blob/master/FileSaver.js */

var saveAs = saveAs || (function(view) {
	"use strict";
	// IE <10 is explicitly unsupported
	if (typeof navigator !== "undefined" && /MSIE [1-9]\./.test(navigator.userAgent)) {
		return;
	}
	var
		  doc = view.document
		  // only get URL when necessary in case Blob.js hasn't overridden it yet
		, get_URL = function() {
			return view.URL || view.webkitURL || view;
		}
		, save_link = doc.createElementNS("http://www.w3.org/1999/xhtml", "a")
		, can_use_save_link = "download" in save_link
		, click = function(node) {
			var event = new MouseEvent("click");
			node.dispatchEvent(event);
		}
		, is_safari = /Version\/[\d\.]+.*Safari/.test(navigator.userAgent)
		, webkit_req_fs = view.webkitRequestFileSystem
		, req_fs = view.requestFileSystem || webkit_req_fs || view.mozRequestFileSystem
		, throw_outside = function(ex) {
			(view.setImmediate || view.setTimeout)(function() {
				throw ex;
			}, 0);
		}
		, force_saveable_type = "application/octet-stream"
		, fs_min_size = 0
		// See https://code.google.com/p/chromium/issues/detail?id=375297#c7 and
		// https://github.com/eligrey/FileSaver.js/commit/485930a#commitcomment-8768047
		// for the reasoning behind the timeout and revocation flow
		, arbitrary_revoke_timeout = 500 // in ms
		, revoke = function(file) {
			var revoker = function() {
				if (typeof file === "string") { // file is an object URL
					get_URL().revokeObjectURL(file);
				} else { // file is a File
					file.remove();
				}
			};
			if (view.chrome) {
				revoker();
			} else {
				setTimeout(revoker, arbitrary_revoke_timeout);
			}
		}
		, dispatch = function(filesaver, event_types, event) {
			event_types = [].concat(event_types);
			var i = event_types.length;
			while (i--) {
				var listener = filesaver["on" + event_types[i]];
				if (typeof listener === "function") {
					try {
						listener.call(filesaver, event || filesaver);
					} catch (ex) {
						throw_outside(ex);
					}
				}
			}
		}
		, auto_bom = function(blob) {
			// prepend BOM for UTF-8 XML and text/* types (including HTML)
			if (/^\s*(?:text\/\S*|application\/xml|\S*\/\S*\+xml)\s*;.*charset\s*=\s*utf-8/i.test(blob.type)) {
				return new Blob(["\ufeff", blob], {type: blob.type});
			}
			return blob;
		}
		, FileSaver = function(blob, name, no_auto_bom) {
			if (!no_auto_bom) {
				blob = auto_bom(blob);
			}
			// First try a.download, then web filesystem, then object URLs
			var
				  filesaver = this
				, type = blob.type
				, blob_changed = false
				, object_url
				, target_view
				, dispatch_all = function() {
					dispatch(filesaver, "writestart progress write writeend".split(" "));
				}
				// on any filesys errors revert to saving with object URLs
				, fs_error = function() {
					if (target_view && is_safari && typeof FileReader !== "undefined") {
						// Safari doesn't allow downloading of blob urls
						var reader = new FileReader();
						reader.onloadend = function() {
							var base64Data = reader.result;
							target_view.location.href = "data:attachment/file" + base64Data.slice(base64Data.search(/[,;]/));
							filesaver.readyState = filesaver.DONE;
							dispatch_all();
						};
						reader.readAsDataURL(blob);
						filesaver.readyState = filesaver.INIT;
						return;
					}
					// don't create more object URLs than needed
					if (blob_changed || !object_url) {
						object_url = get_URL().createObjectURL(blob);
					}
					if (target_view) {
						target_view.location.href = object_url;
					} else {
						var new_tab = view.open(object_url, "_blank");
						if (new_tab == undefined && is_safari) {
							//Apple do not allow window.open, see http://bit.ly/1kZffRI
							view.location.href = object_url
						}
					}
					filesaver.readyState = filesaver.DONE;
					dispatch_all();
					revoke(object_url);
				}
				, abortable = function(func) {
					return function() {
						if (filesaver.readyState !== filesaver.DONE) {
							return func.apply(this, arguments);
						}
					};
				}
				, create_if_not_found = {create: true, exclusive: false}
				, slice
			;
			filesaver.readyState = filesaver.INIT;
			if (!name) {
				name = "download";
			}
			if (can_use_save_link) {
				object_url = get_URL().createObjectURL(blob);
				setTimeout(function() {
					save_link.href = object_url;
					save_link.download = name;
					click(save_link);
					dispatch_all();
					revoke(object_url);
					filesaver.readyState = filesaver.DONE;
				});
				return;
			}
			// Object and web filesystem URLs have a problem saving in Google Chrome when
			// viewed in a tab, so I force save with application/octet-stream
			// http://code.google.com/p/chromium/issues/detail?id=91158
			// Update: Google errantly closed 91158, I submitted it again:
			// https://code.google.com/p/chromium/issues/detail?id=389642
			if (view.chrome && type && type !== force_saveable_type) {
				slice = blob.slice || blob.webkitSlice;
				blob = slice.call(blob, 0, blob.size, force_saveable_type);
				blob_changed = true;
			}
			// Since I can't be sure that the guessed media type will trigger a download
			// in WebKit, I append .download to the filename.
			// https://bugs.webkit.org/show_bug.cgi?id=65440
			if (webkit_req_fs && name !== "download") {
				name += ".download";
			}
			if (type === force_saveable_type || webkit_req_fs) {
				target_view = view;
			}
			if (!req_fs) {
				fs_error();
				return;
			}
			fs_min_size += blob.size;
			req_fs(view.TEMPORARY, fs_min_size, abortable(function(fs) {
				fs.root.getDirectory("saved", create_if_not_found, abortable(function(dir) {
					var save = function() {
						dir.getFile(name, create_if_not_found, abortable(function(file) {
							file.createWriter(abortable(function(writer) {
								writer.onwriteend = function(event) {
									target_view.location.href = file.toURL();
									filesaver.readyState = filesaver.DONE;
									dispatch(filesaver, "writeend", event);
									revoke(file);
								};
								writer.onerror = function() {
									var error = writer.error;
									if (error.code !== error.ABORT_ERR) {
										fs_error();
									}
								};
								"writestart progress write abort".split(" ").forEach(function(event) {
									writer["on" + event] = filesaver["on" + event];
								});
								writer.write(blob);
								filesaver.abort = function() {
									writer.abort();
									filesaver.readyState = filesaver.DONE;
								};
								filesaver.readyState = filesaver.WRITING;
							}), fs_error);
						}), fs_error);
					};
					dir.getFile(name, {create: false}, abortable(function(file) {
						// delete file if it already exists
						file.remove();
						save();
					}), abortable(function(ex) {
						if (ex.code === ex.NOT_FOUND_ERR) {
							save();
						} else {
							fs_error();
						}
					}));
				}), fs_error);
			}), fs_error);
		}
		, FS_proto = FileSaver.prototype
		, saveAs = function(blob, name, no_auto_bom) {
			return new FileSaver(blob, name, no_auto_bom);
		}
	;
	// IE 10+ (native saveAs)
	if (typeof navigator !== "undefined" && navigator.msSaveOrOpenBlob) {
		return function(blob, name, no_auto_bom) {
			if (!no_auto_bom) {
				blob = auto_bom(blob);
			}
			return navigator.msSaveOrOpenBlob(blob, name || "download");
		};
	}

	FS_proto.abort = function() {
		var filesaver = this;
		filesaver.readyState = filesaver.DONE;
		dispatch(filesaver, "abort");
	};
	FS_proto.readyState = FS_proto.INIT = 0;
	FS_proto.WRITING = 1;
	FS_proto.DONE = 2;

	FS_proto.error =
	FS_proto.onwritestart =
	FS_proto.onprogress =
	FS_proto.onwrite =
	FS_proto.onabort =
	FS_proto.onerror =
	FS_proto.onwriteend =
		null;

	return saveAs;
}(
	   typeof self !== "undefined" && self
	|| typeof window !== "undefined" && window
	|| this.content
));
// `self` is undefined in Firefox for Android content script context
// while `this` is nsIContentFrameMessageManager
// with an attribute `content` that corresponds to the window

if (typeof module !== "undefined" && module.exports) {
  module.exports.saveAs = saveAs;
} else if ((typeof define !== "undefined" && define !== null) && (define.amd != null)) {
  define([], function() {
    return saveAs;
  });
}


function download_zip_file(zip_file,file_name) {
	var a = window.document.createElement('a');
	a.href = window.URL.createObjectURL(zip_file, {type: 'application/zip'});
	a.download = file_name;
	a.innerHTML = file_name;
	                        
	var div = document.getElementById("download")
	// Append anchor to body.
	div.appendChild(a)
	div.className = "downloadlink"
	//a.click();
	 //var dispatch = document.createEvent("MouseEvents");
    //dispatch.initEvent("click", true, true);
    //a.dispatchEvent(dispatch);
	
	// Remove anchor from body
	//document.body.removeChild(a)

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
	p.innerHTML = author + "; <em>" + title + "</em>"
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
	p.innerHTML = 	author + "; <em>" + title + "</em>"
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
 	//xmlHttpRqst.open( "GET", "get_results.cgi?id=" + user_id, false ); 
 	xmlHttpRqst.open( "GET", "get_results.cgi?id=" + user_id + "&count=" +query_count, false ); 
 	query_count += 1;
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
					if ('filename' in curr_result) {
						zip_filename = curr_result["filename"]
					
					 	var xhr = CreateXmlHttpObject( );
					 	xhr.responseType = 'blob';


 						xhr.open( "GET", "get_zip.cgi?id=" + user_id, true); 
					 	//xmlHttpRqst.open( "GET", "get_results.cgi", false );
						

						xhr.onload = function (e) {
						  if (xhr.readyState === 4) {
						    if (xhr.status === 200) {
						      //download_zip_file(xhr.response,zip_filename);
						      saveAs(xhr.response,zip_filename);
						    } else {
						      console.error(xhr.statusText);
						    }
						  }
						  	stop();
						};
						xhr.onerror = function (e) {
						  console.error(xhr.statusText);
						};
						xhr.send(null);		

					}
					else {
						stop();
					}
					
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
							author = curr_result['Author'].join()
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