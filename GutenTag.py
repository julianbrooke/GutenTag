# -*- coding: utf-8 -*-

version = "0.1.1"

standalone = False
online = False

import sys

if len(sys.argv) > 1 and sys.argv[1] == "-c":
    config_mode = True
else:
    config_mode = False

if standalone:
    sys.frozen = True
    my_path = sys.executable
    if "/" in my_path:
        my_path = my_path[:my_path.rfind("/") + 1]
    else:
        my_path = my_path[:my_path.rfind("\\") + 1]
    sys.path.insert(0, my_path + "Lib")
    if 'posix' in sys.builtin_module_names:
        import posix
        posix.chdir(my_path)

import zipfile
import cPickle
import time
import gc   
import os
import codecs
import re
import copy
import encodings

import StringIO
import time
import random
import webbrowser
from collections import defaultdict
import SocketServer
import socket
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urllib import unquote,quote
from multiprocessing import cpu_count,Queue,Process,Lock,freeze_support
from nltk.tokenize import regexp
if not standalone:
    import nltk.data
from threading import Thread
import json

gc.disable()

re.DOTALL = True

def has_capital(word):
    return any([letter.isupper() for letter in word])

def alpha_count(word):
    count = 0
    for i in range(len(word)):
        if word[i].isalpha():
            count += 1
    return count


romanNumeralMap = (('M',  1000),
                   ('CM', 900),
                   ('D',  500),
                   ('CD', 400),
                   ('C',  100),
                   ('XC', 90),
                   ('L',  50),
                   ('XL', 40),
                   ('X',  10),
                   ('IX', 9),
                   ('V',  5),
                   ('IV', 4),
                   ('I',  1))



#Define pattern to detect valid Roman numerals
romanNumeralPattern = re.compile("""
    ^                   # beginning of string
    M{0,4}              # thousands - 0 to 4 M's
    (CM|CD|D?C{0,3})    # hundreds - 900 (CM), 400 (CD), 0-300 (0 to 3 C's),
                        #            or 500-800 (D, followed by 0 to 3 C's)
    (XC|XL|L?X{0,3})    # tens - 90 (XC), 40 (XL), 0-30 (0 to 3 X's),
                        #        or 50-80 (L, followed by 0 to 3 X's)
    (IX|IV|V?I{0,3})    # ones - 9 (IX), 4 (IV), 0-3 (0 to 3 I's),
                        #        or 5-8 (V, followed by 0 to 3 I's)
    $                   # end of string
    """ ,re.VERBOSE)

def is_roman(string):
    return romanNumeralPattern.search(string)

def convert_roman(string):
    result = 0
    index = 0
    for numeral, integer in romanNumeralMap:
        while string[index:index+len(numeral)] == numeral:
            result += integer
            index += len(numeral)
    return result



# This class deals with functions for reading Project Gutenberg metadata
class MetadataReader:

    wanted_tags = set(["Author","Title", "LoC Class", "Subject", "Language"])

    def get_metatag_contents(self,html,tag):
        index = html.find('<th scope="row">%s</th>' % tag)
        result = []
        while index != -1:
            result.append(html[html.find("<td>",index) + 4 :html.find("</td>", index)].replace("&amp;","&"))
            index = html.find('<th scope="row">%s</th>' % tag, index + 1)
        return result

    def expand_author(self,tags):
        if "Author" not in tags:
            return
        authors = tags["Author"]
        tags["Author"] = []
        tags["Author Birth"] = []
        tags["Author Death"] = []
        tags["Author Given"] = []
        tags["Author Surname"] = []
        for author in authors:
            parts = author.split(", ")
            birth = None
            death = None
            if len(parts) >= 2:
                if parts[-1].count("-") == 1:
                    birth_string, death_string = parts[-1].split("-")
                    birth_string = birth_string.replace("?", "")
                    birth_string = birth_string.replace("AD", "")
                    if "BC" in birth_string:
                        BC = True
                        birth_string = birth_string.replace("BC"," ")
                    else:
                        BC = False
                    try:
                        birth = int(birth_string)
                        if BC:
                            birth = -birth
                    except:
                        pass

                    death_string = death_string.replace("?", "")
                    death_string = death_string.replace("AD", "")
                    if "BC" in death_string:
                        BC = True
                        death_string = death_string.replace("BC"," ")
                    else:
                        BC = False
                    try:
                        death = int(death_string)
                        if BC:
                            death = -death
                    except:
                        pass                   
                    
                    parts = parts[:-1]
                parts.reverse()
                author = " ".join(parts)
                if len(parts) == 2:
                    tags["Author Given"].append(parts[0])
                    tags["Author Surname"].append(parts[1])
                    
            tags["Author"].append(author)
            tags["Author Birth"].append(birth)
            tags["Author Death"].append(death)

    def get_href_and_charset(self,html_text):
        index = html_text.find("text/plain")
        if index == -1:
            return None,-1
        index = html_text.find('charset="', index)
        if index == -1:
            charset = "utf-8"
            index = html_text.find("text/plain")
        else:            
            charset = html_text[index + 9:html_text.find('"',index + 9)]
        index = html_text.find(' href="', index)
        if index == -1:
            href = None
        else:
            href = html_text[index + 9:html_text.find('"',index + 9)]

        return href, charset

    def get_PG_metadata(self,filename):
        f = codecs.open(filename, encoding="utf-8")
        html_text = f.read()
        f.close()
        tag_dict = {}
        for tag in self.wanted_tags:
            tag_dict[tag] = self.get_metatag_contents(html_text,tag)
        self.expand_author(tag_dict)
        for i in range(len(tag_dict["Title"])):
            tag_dict["Title"][i] = tag_dict["Title"][i].replace("\n","\t")
        href, charset = self.get_href_and_charset(html_text)
        return href,charset,tag_dict


# this class cleans away Project Gutenberg headers and footers, including copyright and transcriber notes
class TextCleaner:
    junk_indicators = ("project gutenberg"," etext"," e-text",
                            "http:","distributed proofreading",
                            "distributed\nproofreading", " online"
                            "html","utf-8","ascii","transcriber's note",
                            "scanner's note", "\\.net","\\.org","\\.com",
                            "\\.edu","www\\.", "electronic version",
                            " email","\\.uk","digitized", "\n\nproduced by",
                            "david reed", "\ntypographical errors corrected",
                            "\[note: there is a","etext editor's","u.s. copyright",
                            "\nerrata"," ebook"," e-book")
                
    
    def clean_text(self,text):
        text = text.replace("\r\n","\n").replace("\r","\n") # normalize lines
        text = re.sub("\n[ *-]+\n","\n\n",text) # get rid of explicit section breaks
        #text = re.sub("\[Illustration:?[^\]]*\]","",text)
        text = re.sub("<<[^>]+>>","",text)
        text = re.sub("[^_]_______________________________________.*_________________________________[^_]","\n\n",text)
        lower_text = text.lower()
        all_junk_indicies = [0, len(text)]
        for junk_indicator in self.junk_indicators:
            all_junk_indicies.extend([m.start() for m in re.finditer(junk_indicator,lower_text)])
        all_junk_indicies.sort()
        best_points = None
        best_length = 0
        for i in range(len(all_junk_indicies) - 1):
            if all_junk_indicies[i+1] - all_junk_indicies[i] > best_length:
                best_points = [all_junk_indicies[i],all_junk_indicies[i+1]]
                best_length = all_junk_indicies[i+1] - all_junk_indicies[i]
        found = False
        best_length = float(best_length)
        if best_length < 5000: # too small for general method to work reliably
            m = re.search("end of [^\\n]*project gutenberg",lower_text)
            if m:
                best_points[1] = m.start()
                i = 0
                while all_junk_indicies[i] < best_points[1] - 100:
                    i += 1
                best_points[0] = all_junk_indicies[i-1]
            else:
                return ""

        i = 4
        while not found:
            looking_for = "\n"*i
            result = text.find(looking_for, best_points[0])
            if result != -1 and ((best_points[1] - result)/best_length > 0.98 or i == 1):
                found = True
            i -= 1

        return text[result:text.rfind("\n", 0, best_points[1])].strip()


# This guesses at the gender of a person based on their name         
class GenderClassifier:
    def __init__(self):
        f = open("resources/femaleFirstNames.txt")
        self.female_first_names = set()
        for line in f:
            self.female_first_names.add(line.strip())
        f.close()
        '''
        f = open("maleFirstNames.txt")
        for line in f:
            self.female_first_names.discard(line.strip())
        f.close()
        '''

    def classify(self,word):
        if word in self.female_first_names:
            return "female"
        else:
            return "male"


# this class wraps everything related to genre classification. Not actually
# functional because genres are pre-calculated using separate script

class GenreClassifier:

    common_words = set(["how","you","the","a","it","he","she","i","they","we","at","and","but","when","there","as","if","after","before","this","that","all","what","to","from","such","here","with","for","some","where","now","dear","yours","your","january","febuary","march","april","may","june","july","august","september","october","november","december","monday","tuesday","wednesday","thursday","friday","saturday","sunday"])
    likely_delimin = set([".","-",":","<","(","_","["])
    narrative_words = set(["said","asked","replied","answered","cried","answered","responded","added","ejaculated","rejoined","inquired"])
    fiction_title = set(["novel","stories","story","adventures","tale","tales","mystery"])
    nonfiction_title = set(["discourses", "autobiography","biography","diary","diaries","letters","essay","essays","record","history","speech","speeches","talks","recollections","memoirs","sermons","life"])
    poetry_title = set(["poem","poetry", "verse", "ballad", "poetical","ode"])
    play_title = set(["play","drama","acts"])
    end_words = set(["the end","end","finis","fin"])

    def __init__(self,decision_tree_filename):
        self.node_dict = {}
        f = open(decision_tree_filename)
        for line in f:
            stuff = line.strip().split(",")
            if len(stuff) == 2:
                self.node_dict[int(stuff[0])] = [stuff[1]]
            else:
                self.node_dict[int(stuff[0])] = [int(stuff[1]),int(stuff[2]),stuff[3],float(stuff[4])]
            


    def get_feature_dict(self,text,tags):
        feature_dict = {}
        lines = text
        total_lines = 0.0
        total_paragraphs = 0.0
        expected_no_capital = 0.0
        title_words = tags["Title"][0].replace(":"," :").replace(";", " ;").replace("  "," ").lower().split()
        
        feature_dict["title_volume"] = 0
        feature_dict["title_twoparts"] = "\t" in tags["Title"][0]
        feature_dict["fiction_title"] = 0
        feature_dict["nonfiction_title"] = 0
        feature_dict["play_title"] = 0
        feature_dict["poetry_title"] = 0

        feature_dict["title_length"] = len(title_words)
        found_key = False
        for word in title_words:
            if word == "volume" or word == "vol.":
                feature_dict["title_volume"] = 1
            elif word == ":" or word == ";" or word == u"—":
                feature_dict["title_twoparts"] = 1
            elif word in self.nonfiction_title and not found_key:
                feature_dict["nonfiction_title"] = 1
                found_key = True
            elif word in self.fiction_title and not found_key:
                feature_dict["fiction_title"] = 1
                found_key = True
            elif word in self.play_title and not found_key:
                feature_dict["play_title"] = 1
                found_key = True
            elif word in self.poetry_title and not found_key:
                feature_dict["poetry_title"] = 1
                found_key = True
        try:
            if tags["Author"][0] in tags["Title"][0]:
                feature_dict["author_in_title"] = 1
            else:
                feature_dict["author_in_title"] = 0
        except:
            feature_dict["author_in_title"] = 0
        
        feature_dict["capital_line_count"] = 0
        feature_dict["comma_line_count"] = 0
        feature_dict["dash_line_count"] = 0
        feature_dict["you_line_count"] = 0
        feature_dict["I_line_count"] = 0
        feature_dict["she_line_count"] = 0
        feature_dict["line_number_count"] = 0
        feature_dict["indent_count"] = 0
        feature_dict["uncommon_repeat_count"] = 0
        feature_dict["two_capital_count"] = 0
        feature_dict["act_count"] = 0
        feature_dict["chapter_count"] = 0
        feature_dict["quote_count"] = 0
        feature_dict["early_delim_count"] = 0
        feature_dict["headers"] = 0.0
        feature_dict["repeated_headers"] = 0
        feature_dict["longest_quote_string"] = 0
        feature_dict["other_sent_punc"] = 0
        feature_dict["end"] = 0
        feature_dict["narrative_words"] = 0
        feature_dict["illustrations"] = 0
        feature_dict["avg_paragraph_len"] = 0
        feature_dict["asides_count"] = 0

        start_word_list = set()
        repeated_list = {}
        repeated_header = set()
        indented = False
        last_indented = False
        quote_string_count = 0
        for i in range(len(lines)):
            if lines[i].strip():
                total_lines += 1
                feature_dict["avg_paragraph_len"] += 1
                if lines[i][0] == " ":
                    feature_dict["indent_count"] += 1
                    last_indented = indented
                    indented = True
                else:
                    indented = False
                if '"' in lines[i]:
                    feature_dict["quote_count"] += 1
                for word in self.narrative_words:
                    if word in lines[i]:
                        feature_dict["narrative_words"] += 1
                if "!" in lines[i] or "?" in lines[i]:
                    feature_dict["other_sent_punc"] += 1
                #lines[i] = lines[i].strip()
                curr_line = lines[i]
                while "  " in curr_line:
                    curr_line  = curr_line.replace("  "," ")
                    
                curr_line = curr_line.strip()
                if "I " in curr_line or "I'" in curr_line or "my " in curr_line or " me " in curr_line:
                    feature_dict["I_line_count"] += 1
                if curr_line.startswith("[Illustration"):
                    feature_dict["illustrations"] += 1
                elif ("(" in curr_line and curr_line.find(")", max(curr_line.find("(") - 3,0), min(curr_line.find("(") + 3, len(curr_line))) == -1) or ("[" in curr_line and curr_line.find("]", max(curr_line.find("[") - 3,0), min(curr_line.find("[") + 3,len(curr_line))) == -1):
                    feature_dict["asides_count"] += 1
                 
                words = curr_line.split(" ")
                curr_line = curr_line.lower()
                if words[-1].endswith(","):
                    feature_dict["comma_line_count"] += 1
                if words[-1].isdigit():
                    lower_line = lines[i].lower()
                    if not "act" in lower_line and not "chapter" in lower_line and not "scene" in lower_line:
                        feature_dict["line_number_count"] += 1
                if  i > 0 and lines[i-1] and len(words) > 4 and not (lines[i-1].endswith(".") or lines[i-1].endswith("?") or lines[i-1].endswith("!")):
                    expected_no_capital += 1
                    if words[0].isalpha() and has_capital(words[0]):
                        feature_dict["capital_line_count"] += 1
                if curr_line in self.end_words:
                    feature_dict["end"] = 1
                if "you" in curr_line:
                    feature_dict["you_line_count"] += 1
                if "she " in curr_line or "her " in curr_line:
                    feature_dict["she_line_count"] += 1
                if "--" in curr_line:
                    feature_dict["dash_line_count"] += 1
                if i > 0 and (not lines[i-1] or (indented and not last_indented)):
                    total_paragraphs += 1

                    if (words[0].lower() == "act" or words[0].lower() == "scene")  and i != len(lines) -1 and not lines[i+1].strip():
                        feature_dict["act_count"] += 1
                    elif words[0].lower() == "chapter" and i != len(lines) -1 and not lines[i+1].strip():
                        feature_dict["chapter_count"] += 1
                    elif words[0].lower() in start_word_list:
                        feature_dict["uncommon_repeat_count"] += 1
                        repeated_list[words[0].lower()] = repeated_list.get(words[0].lower(),0) + 1
                    elif (words[0][0].isalpha() or words[0][0] == "_")   and len(words[0]) > 2 and words[0].lower() not in self.common_words:
                        start_word_list.add(words[0].lower())
                    if len(words) > 2 and not words[0].startswith('"') and has_capital(words[0]) and has_capital(words[1]):
                        feature_dict["two_capital_count"] += 1
                    if has_capital(words[0]) and alpha_count(words[0]) > 1 and (not self.likely_delimin.isdisjoint(words[0]) or (len(words) > 1 and not self.likely_delimin.isdisjoint(words[1]))):
                        feature_dict["early_delim_count"] += 1
                    if i < len(lines) -1 and not lines[i+1].strip() and len(words) < 5:
                        feature_dict["headers"] += 1
                        if lines[i] in repeated_header:
                            feature_dict["repeated_headers"] += 1
                        else:
                            repeated_header.add(lines[i])

                    if curr_line.startswith('"'):
                        quote_string_count += 1
                        if quote_string_count > feature_dict["longest_quote_string"]:
                            feature_dict["longest_quote_string"] = quote_string_count
                    else:
                        quote_string_count = 0
            else:
                pass

        try:                
            feature_dict["capital_line_count"] /= expected_no_capital
        except:
            pass
        try:
            feature_dict["comma_line_count"] /= total_lines
            feature_dict["line_number_count"] /= total_lines
            feature_dict["indent_count"] /= total_lines
            feature_dict["quote_count"] /= total_lines
            feature_dict["other_sent_punc"] /= total_lines
            feature_dict["narrative_words"] /= total_lines
            feature_dict["dash_line_count"] /= total_lines
            feature_dict["you_line_count"] /= total_lines
            feature_dict["I_line_count"] /= total_lines
            feature_dict["she_line_count"] /= total_lines
            feature_dict["asides_count"] /= total_lines
        except:
            pass
        try:
            feature_dict["repeated_headers"] /= feature_dict["headers"]
        except:
            pass
        try:
            feature_dict["uncommon_repeat_count"] /= total_paragraphs
            feature_dict["two_capital_count"] /= total_paragraphs
            feature_dict["early_delim_count"] /= total_paragraphs
            feature_dict["avg_paragraph_len"] = (feature_dict["avg_paragraph_len"] - feature_dict["headers"]) / (total_paragraphs - feature_dict["headers"])
            feature_dict["headers"] /= total_paragraphs
        except:
            pass


        return feature_dict

    def get_classification(self,feature_dict,node):
        if len(node) == 1:
            return node[0]
        else:
            if feature_dict[node[2]] <= node[3]:    
                return self.get_classification(feature_dict,self.node_dict[node[0]])
            else:
                return self.get_classification(feature_dict,self.node_dict[node[1]])


    def classify_genre(self,text,tags):
        feature_dict = self.get_feature_dict(text,tags)
        return self.get_classification(feature_dict,self.node_dict[0])






# Tokenizer built on top of NLTK tokenizer does a few special things to work
# better with PG texts (for instance, preserves hyphenated words and direction
# of quotes)
class Tokenizer:
    
    base_contractions = ["s", "ll", "d", "re", "m", 've']
    base_abbreviations = ["Mr.","Mrs.","Dr.","Ms.","Rev.","St.","etc.","Prof."
                              "Ltd.","Jr.","Vol.","lbs.","pp.","pg."]



    def __init__(self):
        

        self.contractions = set()
        for contraction in self.base_contractions:
            self.contractions.add(contraction)
            self.contractions.add(contraction.upper())

        
        self.abbreviations = set()
        for abbreviation in self.base_abbreviations:
            self.abbreviations.add(abbreviation)
            self.abbreviations.add(abbreviation.upper())

        

        self.left_single_quote = re.compile("(\s|^)'([^ ])")
        self.right_single_quote = re.compile("([^ ])'($|[\s])")

        self.left_double_quote = re.compile('(\s|^)"([^ ])')
        self.right_double_quote = re.compile('([^ ])"($|[\s])')
        self.left_bracket = re.compile('([,-])\[')
        self.right_bracket = re.compile('\]([,-])')      
        f = open('resources/english.pickle')
        self.sentence_tokenizer = cPickle.load(f)
        f.close()
        self.word_tokenizer = regexp.WordPunctTokenizer()


    def fix_quotes(self,raw_text):
        return self.left_double_quote.sub(u'\\1 “ \\2',self.right_double_quote.sub(u'\\1 ” \\2',self.left_single_quote.sub(u'\\1 ‘ \\2',self.right_single_quote.sub(u'\\1 ’ \\2',raw_text))))


    def fix_brackets(self,raw_text):
        return self.left_bracket.sub(u'\\1 [',self.right_bracket.sub(u'] \\1',raw_text))

    def tokenize_span(self,raw_text):
        new_text = self.fix_quotes(raw_text)
        new_text = self.fix_brackets(raw_text)
        new_text = new_text.replace("_","")
        all_sentences = []
        sentences = self.sentence_tokenizer.tokenize(new_text)
        new_sentences = []
        i = 0
        for sentence in sentences:
            sentence = self.word_tokenizer.tokenize(sentence.strip().replace("--",u"—").replace("-", "hYpppHeN"))
            i = 0
            if not sentence:
                continue
            if "hYpppHeN" in sentence[0]:
                sentence[0] = sentence[0].replace("hYpppHeN", "-")
            while i < len(sentence) -2:
                if sentence[i+1] == "'" and sentence[i+2] in self.contractions:
                    sentence[i + 1] += sentence[i+2]
                    del sentence[i+2]                      
                elif sentence[i+1] == "'" and sentence[i+2] == 't' and sentence[i].endswith('n'):
                    if not sentence[i] == "can":
                        sentence[i] = sentence[i][:-1]
                    sentence[i+1] = "n't"
                    del sentence[i+2]
                elif sentence[i+1] == ".":
                    sentence[i] += "."
                    del sentence[i+1]  
                if sentence[i+1].startswith("hYpppHeN"):
                    sentence= sentence[:i+1] + ["-"] + [sentence[i+1][8:]] + sentence[i+2:]
                if sentence[i+1].endswith("hYpppHeN"):
                    sentence= sentence[:i+1] + [sentence[i+1][:-8]] + ["-"] + sentence[i+2:]
                if "hYpppHeN" in sentence[i+1]:
                    sentence[i+1] = sentence[i+1].replace("hYpppHeN", "-")
                i+= 1
            if "hYpppHeN" in sentence[-1]:
                sentence[-1] = sentence[-1].replace("hYpppHeN", "-")
            all_sentences.append(sentence)
        return all_sentences


# This class is GutenTag's basic tag representation: a tag consists of a two
# indicies indicating the start and end of the tag (in a list of tokens), the
# main tag, and then a dictionary of attributes.Depth and plike are used for
# indentation issues in TEI output (depth indicates the level of indentation,
# if applicable, plike tags are indented but the tags inside them are not)

class Tag:

    def __init__(self,start,end,tag,attributes):
        self.start = start
        self.end = end
        self.tag = tag
        self.attributes = attributes
        self.depth = 99
        self.plike = False

    def __cmp__(self,other):
        if self.start < other.start:
            return -1
        elif self.start > other.start:
            return 1
        else:
            if self.end > other.end:
                return -1
            elif self.end < other.end:
                return 1
            else:
                if self.depth < other.depth:
                    return -1
                elif other.depth > self.depth:
                    return 1
                else:
                    return 0


    def get_start_tag(self):
        if self.attributes:
            return "<%s %s>" % (self.tag," ".join([key + '="' + unicode(value) + '"' for key,value in self.attributes.iteritems()]))                
        else:
            return "<%s>" % (self.tag)

    def get_end_tag(self):
        return "</%s>" % (self.tag)

    def add_attribute(self,key,value):
        if self.attributes == None:
            self.attributes = {}
        self.attributes[key] = value

    def get_single_tag(self):
        if self.tag == "div" and self.attributes and "type" in self.attributes:
            return "div:" + self.attributes["type"]
        else:
            return self.tag


# the representation of a text, just a collection of tokens and tags (in
# no particular order)

class Text:

    def __init__(self,tokens,tags):
        self.tags = tags
        self.tokens = tokens


def has_all_features(index,features,feature_dict):
    for feature in features:
        if index not in feature_dict[feature]:
            return False
    return True

def has_no_features(index,features,feature_dict):
    for feature in features:
        if index in feature_dict[feature]:
            return False
    return True

def has_most_features(index,features,feature_dict):
    has_one = False
    missing_one = False
    for feature in features:
        if index in feature_dict[feature]:
            has_one = True
        else:
            if not missing_one:
                missing_one=True
            else:
                return False
    if has_one:
        return True
    else:
        return False


# Wraps everything related to structural tagging. The main logic is
# 1. Extract line-by-line features from text
# 2. Decide on front/back boundaries based on those features (and text boundaries if multiple texts)
# 3. Go through front and back parts of text and create initial tags for relevant
# elements (this involves spreading line features across lines and paragraphs)
# 4. Go through body, and find large structural elements (chapters, etc.)
# 5. Go through entire text, tokenizing paragraphs and other elements (including
# (those identified in 3 and 4) and creating text representation 

class StructureTagger:

    table_of_contents = set(["contents","table of contents"])

    numbers = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
               "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,
               "fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,
               "eighteen":18,"nineteen":19,"twenty":20,"thirty":30,"forty":40,
               "fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90}

    tens_numbers = set(["twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"])

    ordinals = {"first":1,"second":2,"third":3,"forth":4,"fifth":5,"sixth":6,"seventh":7,"eighth":8,"ninth":9,"prima":1,"primus":1,"secundus":2,"tertius":3,"quartus":4,"quintus":5,"sextus":6}

    list_of_illustrations = set(["illustrations","list of illustrations", "table of illustrations", "portraits"])
    endnotes = set(["endnotes","notes", "note", "bibliographical note"])

    stage_start =  re.compile("enter|exit|curtain|exeunt")
    setting_start = re.compile("setting|the time|the setting|the place|the scene|scene:|scene\.")
    setting_phrase = re.compile("takes place|is set in|the setting is|the setting of the play|the action ")
    cities = ["London","New York","Oxford","Cambridge","Boston","Philadelphia","San Francisco","Toronto","Los Angeles","Chicago","Sydney","Auckland","Dublin"]
    countries = ["U.S.A","U.S.","United States","United States of America","America","Canada","England","Britan","United Kingdom", "U.K.", "Australia", "New Zealand"]
    sent_punct = set([".","?","!"])
    city = re.compile("|".join(cities).lower())
    copy_right = re.compile("all rights reserved|copyright")
    published = re.compile("publish(er|ed by)|print(er|ed by)| press[^\w]")
    dedication = re.compile("dedicated to|inscribed to|in memory of")
    series = re.compile("same author|series|other titles|other books|(play|book|work)s (by|of)|author of|'s (books|plays)|books for")
    next_word = re.compile("\W(\w+)($|\W)")
    next_next_word = re.compile("\W\w+\W(\w+)($|\W)")
    first_word = re.compile("^[^A-Za-z]*([A-Za-z]+)($|[^A-Za-z])")
    year = re.compile("(^|[^0-9])1[0-9]{3}($|[^0-9])")
    act = re.compile("(^|\W|_)act(us)?($|\W|_)")
    scene = re.compile("(^|\W|_)scen[ea]($|\W|_)")
    characters = re.compile(u"actors|characters|persons|dramatis person(ae|æ)|(^|\W)cast($|\W)")
    performance = re.compile("theat(er|re)|performance|presented|performed|produced (by|for)")
    low_numbers = re.compile("(one|two|three|four|five|six|first|second|third|forth|fifth|sixth|prima|primus|secundus|quartus|quintus|tertius|sextus|1|2|3|4|5|6|(\W)i($|\W)|(\W)ii($|\W)|iii|(\W)iv($|\W)|(\W)v($|\W)|(\W)vi($|\W))") 
    early_period = re.compile("^(\W*\w+( \w+)?|[^a-z]+)\.")
    early_colon = re.compile("^(\W*\w+( \w+)?|[^a-z]+):")
    text_after_delim = re.compile("^(\W*\w+(\W+\w+)?|[^a-z]+)[.:].*[a-z].*")
    parens_after_capital = re.compile("^[A-Z'_ ]+[A-Z][A-Z'_ ]+(\(|\[)")
    indents = re.compile("^( *)[^ ]")
    first_letter = re.compile("[A-Za-z]")
    non_letters = re.compile("[^A-Za-z]")
    
    
    

    def __init__(self,options,tokenizer):
        self.options = options
        self.tokenizer = tokenizer

    def get_structural_features(self,text_lines,global_tags):
        feature_dict = {}
        feature_dict["upper_case"] = set()
        feature_dict["blank_lines"] = set()
        feature_dict["table_of_contents"] = set()
        feature_dict["author"] = set()
        feature_dict["title"] = set()
        feature_dict["dedication"] = set()
        feature_dict["introduction"] = set()
        feature_dict["preface"] = set()
        feature_dict["publisher"] = set()
        feature_dict["chapter"] = {}
        feature_dict["by"] = set()
        feature_dict["blank_set"] = set()
        feature_dict["year"] = set()
        feature_dict["year_only"] = set()
        feature_dict["illustration"] = set()
        feature_dict["list_of_illustrations"] = set()
        feature_dict["footnote"] = set()
        feature_dict["starts_lower"] = set()
        feature_dict["total_length"] = len(text_lines)
        feature_dict["starts_upper"] = set()
        feature_dict["quoted"] = set()
        feature_dict["city"] = set()
        feature_dict["copy_right"] = set()
        feature_dict["series"] = set()
        feature_dict["attribution"] = set()
        feature_dict["illustrated"] = set()
        feature_dict["dust_jacket"] = set()
        feature_dict["book"] = {}
        feature_dict["part"] = {}
        feature_dict["starts_with_roman"] = set()
        feature_dict["epilogue"] = set()
        feature_dict["prologue"] = set()
        feature_dict["appendix"] = set()
        feature_dict["afterword"] = set()
        feature_dict["endnotes"] = set()
        feature_dict["glossary"] = set()
        feature_dict["bibliography"] = set()
        feature_dict["index"] = set()
        feature_dict["the_end"] = set()
        feature_dict["single_line_para"] = set()
        feature_dict["indents"] = {}
        feature_dict["ends_with_page"] = set()
        feature_dict["act"] = {}
        feature_dict["scene"] = {}
        feature_dict["character_list"] = set()
        feature_dict["performance"] = set()
        feature_dict["starts_capitalized"] = set()
        feature_dict["early_period"] = set()
        feature_dict["early_colon"] = set()
        feature_dict["text_after_delim"] = set()
        feature_dict["surrounded_by_underscore"] = set()
        feature_dict["start_with_parens"] = set()
        feature_dict["start_with_bracket"] = set()
        feature_dict["short_line"] = set()
        feature_dict["setting_word"] = set()
        feature_dict["stage_word"] = set()
        feature_dict["curtain"] = set()
        feature_dict["parens_after_capital"] = set()
        feature_dict["setting_phrase"] = set()
        feature_dict["ends_with_sent_punct"] = set()
        feature_dict["not_front_lines"] = {}
        feature_dict["double_act_or_scene"] = set()


        has_front_header = False
        in_front_section = False
        has_front_indicator = False
        paragraph_line_count = 0
        not_front_lines = 0 # counts lines up to this point which don't seem like
        seen_act = False    # part of front
        seen_scene = False
        
            
        title = self.non_letters.sub("",global_tags["Title"][0].lower())  
        blank_count = 0
        for i in range(len(text_lines)):
            if not text_lines[i]:
                feature_dict["blank_lines"].add(i)
                blank_count += 1
                continue
            if blank_count > 0:
                if blank_count not in feature_dict:
                    feature_dict[blank_count] = set()
                feature_dict[blank_count].add(i)
                feature_dict["blank_set"].add(blank_count)
                if not has_front_indicator and not has_front_header and not in_front_section:
                    not_front_lines += paragraph_line_count
                feature_dict["not_front_lines"][i] = not_front_lines
                paragraph_line_count = 0
                has_front_indicator = False
                if blank_count > 1:
                    in_front_section = False
            if has_front_header:
                if not text_lines[i].isupper() or (i < len(text_lines) -1 and text_lines[i+1]):
                    has_front_header = False
                    in_front_section = True
            paragraph_line_count += 1
            blank_count = 0
            indents = self.indents.search(text_lines[i])
            if indents:
                indents = indents.group(1)
                if len(indents) not in feature_dict["indents"]:
                    feature_dict["indents"][len(indents)] = set()
                feature_dict["indents"][len(indents)].add(i)
            if (i == 0 or not text_lines[i-1]) and text_lines[i] and (i == len(text_lines) -1 or not text_lines[i+1]):
                feature_dict["single_line_para"].add(i)
            if text_lines[i].isupper():
                feature_dict["upper_case"].add(i)
                if (i > 0 and not text_lines[i - 1]) and (i < len(text_lines) - 1 and not text_lines[i + 1]):
                    in_front_section = False
            try:
                first_letter = self.first_letter.search(text_lines[i]).group(0)
            except:
                first_letter = ""
            if first_letter.islower() and i < 200:
                feature_dict["starts_lower"].add(i)
            if first_letter.isupper():
                feature_dict["starts_upper"].add(i)
            if text_lines[i].startswith("                     ") or  text_lines[i].strip().startswith("--"):
                feature_dict["attribution"].add(i)                
            if (i == 0 or text_lines[i-1] in feature_dict["blank_lines"]) and text_lines[i].startswith("To ") or text_lines[i].startswith("TO "):
                #has_front_indicator = True
                feature_dict["dedication"].add(i) 

            if text_lines[i].startswith("By"):
                has_front_indicator = True
                feature_dict["by"].add(i)



            if "." in text_lines[i] and is_roman(text_lines[i][:text_lines[i].find(".")].strip()):                
                feature_dict["starts_with_roman"].add(i)

            if text_lines[i].endswith(" PAGE"):
                feature_dict["ends_with_page"].add(i)
                             
            line = text_lines[i].lower().strip(".:;_ ")

            if line.startswith("[") and "illustration" in line:
                feature_dict["illustration"].add(i)

            if line.startswith("[") and "footnote" in line:
                feature_dict["footnote"].add(i)
            
            if text_lines[i].startswith("Illustrated by") or text_lines[i].startswith("Illustrations by"):
                feature_dict["illustrated"].add(i)
                has_front_indicator = True
                
            if line.startswith("preface") or line.startswith("to the reader") or line.endswith("to the reader") or (line.startswith("history of") and "history of" not in global_tags["Title"][0].lower()):
                feature_dict["preface"].add(i)
                has_front_header = True
            if line.startswith("introduction") or line.startswith("foreword"):
                feature_dict["introduction"].add(i)
                has_front_header = True
            for feature in ["prologue","epilogue","appendix","afterword","glossary","bibliography","index","afterword"]:
                if line == feature or (line.startswith(feature) and i in feature_dict["upper_case"]):
                    feature_dict[feature].add(i)

            if line in self.endnotes or line.startswith("notes on"):
                feature_dict["endnotes"].add(i)
            if line.startswith("dust jacket"):
                feature_dict["dust_jacket"].add(i)
                has_front_header = True
            if line in self.table_of_contents or line.startswith("contents of") or (line == "index" and i < len(text_lines)/3):
                feature_dict["table_of_contents"].add(i)
                has_front_header = True
            if global_tags["Author"] and global_tags["Author"][0].lower() in line:
                has_front_indicator = True
                feature_dict["author"].add(i)
            only_letter_line = self.non_letters.sub("",line.lower())
            if (len(only_letter_line) > 5 and only_letter_line in title or (only_letter_line.startswith(title))):
                feature_dict["title"].add(i)
                has_front_indicator = True
            if self.published.search(line):
                feature_dict["publisher"].add(i)
                has_front_indicator = True
            if self.dedication.search(line):
                feature_dict["dedication"].add(i)
                has_front_indicator = True

            if (line == "the end" or line == "fin" or line == "finis") and i in feature_dict["upper_case"] and i - 1 in feature_dict["blank_lines"]:
                feature_dict["the_end"].add(i)

            if self.series.search(line):
                if i not in feature_dict["title"]:
                    feature_dict["series"].add(i)
            if self.city.search(line):
                feature_dict["city"].add(i)
                #has_front_indicator = True

            if self.copy_right.search(line):
                feature_dict["copy_right"].add(i)
                has_front_indicator = True

            if i - 1 in feature_dict["blank_lines"] and (line.startswith('"') and (line.endswith('"') or (i+1 < len(text_lines) and text_lines[i+1].endswith('"') or (i+2 < len(text_lines) and text_lines[i+2].endswith('"'))))):
                feature_dict["quoted"].add(i)
                               

            if line and line[-1] in self.sent_punct:
                feature_dict["ends_with_sent_punct"].add(i)
                
            if i in feature_dict["starts_upper"]:
                for div in ["chapter","book","part"]:
                    if line.startswith(div + " "):
                        try:
        
                            after_chapter = self.next_word.search(line)
                            if after_chapter:
                                after_chapter = after_chapter.group(1)
                            else:
                                after_chapter = ""
                            after_chapter = after_chapter.strip(".")
                            if after_chapter.isdigit():
                                chapter_num = int(after_chapter)
                            elif is_roman(after_chapter.upper()):
                                chapter_num = convert_roman(after_chapter.upper())
                            elif after_chapter in self.numbers:
                                chapter_num = self.numbers[after_chapter]
                                if after_chapter in self.tens_numbers:
                                    after_first_num = self.next_next_word.search(line)
                                    if after_first_num:
                                        after_first_num = after_first_num.group(1)
                                    else:
                                        after_first_num = ""
                                    if after_first_num in self.numbers:
                                        chapter_num += self.numbers[after_first_num]
                                    
                            else:
                                chapter_num = "?"

                            if chapter_num != "?":
                                feature_dict[div][i] = chapter_num
                        except:
                            pass

            if line.isdigit() and int(line) < 100:
                if "digit_only" not in feature_dict:
                    feature_dict["digit_only"] = {}
                try:
                    feature_dict["digit_only"][i] = int(line)
                except:
                    pass

            if is_roman(line.upper()):
                if "roman_only" not in feature_dict:
                    feature_dict["roman_only"] = {}
                feature_dict["roman_only"][i] = convert_roman(line.upper())


            if line in self.numbers:
                if "wordnum_only" not in feature_dict:
                    feature_dict["wordnum_only"] = {}
                feature_dict["wordnum_only"][i] = self.numbers[line]
                

            if self.year.search(line):
                feature_dict["year"].add(i)
                has_front_indicator = True
                if len(line) == 4:
                    feature_dict["year_only"].add(i)

            if line in self.list_of_illustrations:
                feature_dict["list_of_illustrations"].add(i)

            if global_tags["Genre"] == "play":
                
                 if self.parens_after_capital.search(text_lines[i]):
                    feature_dict["parens_after_capital"].add(i)

                 if line == "curtain":
                     feature_dict["curtain"].add(i)
                 if not "end of" in line:
                     if self.act.search(line):
                        if line.find("act") < 12 and ("ACT" in text_lines[i] or "Act" in text_lines[i]):
                            found_act = True
                        else:
                            found_act = False
                     else:
                         found_act = False
                     if self.scene.search(line):
                         if (found_act or line.find("scen") < 12) and ("SCEN" in text_lines[i] or "Scen" in text_lines[i]):
                             found_scene = True
                         else:
                             found_scene = False
                     else:
                         found_scene = False
                 if self.characters.search(line):
                     has_front_header = True
                     feature_dict["character_list"].add(i)


                 if self.performance.search(line):
                     has_front_indicator = True
                     feature_dict["performance"].add(i)


                 first_word = self.first_word.search(text_lines[i])
                 if first_word:
                     first_word = first_word.group(1)
                     if len(first_word) > 1 and first_word.isupper():
                        feature_dict["starts_capitalized"].add(i)

                 if self.setting_start.match(line) or line == "scene":
                    has_front_indicator = True
                    feature_dict["setting_word"].add(i)

                 if self.stage_start.match(line):
                    feature_dict["stage_word"].add(i)

                 if self.setting_phrase.search(line):
                    feature_dict["setting_phrase"].add(i)

                 if self.early_period.search(text_lines[i]) and i in feature_dict["starts_upper"]:
                    feature_dict["early_period"].add(i)
                    if self.text_after_delim.search(text_lines[i]):
                        feature_dict["text_after_delim"].add(i)
                 if self.early_colon.search(text_lines[i]) and i in feature_dict["starts_upper"]:
                    feature_dict["early_colon"].add(i)
                    if self.text_after_delim.search(text_lines[i]):
                        feature_dict["text_after_delim"].add(i)
                 if text_lines[i].strip().startswith("_") and text_lines[i].strip().endswith("_"):
                    feature_dict["surrounded_by_underscore"].add(i)
                 if text_lines[i].strip().startswith("("):
                    if i - 1 in feature_dict["blank_lines"]:
                        feature_dict["start_with_parens"].add(i)
                 if text_lines[i].strip().startswith("["):
                    if i - 1 in feature_dict["blank_lines"]:
                        feature_dict["start_with_bracket"].add(i)
                                        
                 if len(line) < 15:
                    feature_dict["short_line"].add(i)

                 if found_act or found_scene:
                     matches = self.low_numbers.findall(line)
                     if matches:
                         good_matches = []
                         for match in matches:
                             try:
                                 match.isdigit()
                             except:
                                 match = match[0].strip(" ")
                             if (found_act and abs(line.find(match) - line.find("act")) < 10 or (found_scene and abs(line.find(match) - line.find("scen")) < 10)):
                                 good_matches.append(match)

                         matches = good_matches
                         if not matches:
                             continue
                                 
                         for j in range(len(matches)):
                             if matches[j].isdigit():
                                 matches[j] = int(matches[j])
                             elif matches[j] in self.numbers:
                                 matches[j] = self.numbers[matches[j]]
                             elif matches[j] in self.ordinals:
                                 matches[j] = self.ordinals[matches[j]]
                             else:
                                 matches[j] = convert_roman(matches[j].upper())
                         if found_act:
                             feature_dict["act"][i] = matches[0]
                             if seen_act:
                                 feature_dict["double_act_or_scene"].add(i)
                                 has_front_indicator = True
                             seen_act = True
                         if found_scene:
                             if found_act and len(matches) >= 2:
                                 feature_dict["scene"][i] = matches[1]
                             else:
                                 feature_dict["scene"][i] = matches[0]
                             if seen_scene:
                                 feature_dict["double_act_or_scene"].add(i)
                                 has_front_indicator = True
                             seen_scene = True
                 else:
                     seen_act = False
                     seen_scene = False
                                        
                                      
        # No explicit chapters, use any regular numbers                                      
        if global_tags["Genre"] == "fiction" and len(feature_dict["chapter"]) < 3:
            if "wordnum_only" in feature_dict and len(feature_dict["wordnum_only"]) > 5:
                feature_dict["chapter"] = feature_dict["wordnum_only"]
            if "roman_only" in feature_dict and len(feature_dict["roman_only"]) > 5:
                feature_dict["chapter"] = feature_dict["roman_only"]
            if "digit_only" in feature_dict and len(feature_dict["digit_only"]) > 5:
                feature_dict["chapter"] = feature_dict["digit_only"]                        
                             
        
        return feature_dict




    common_front_elements = ["author","title","publisher","by","performance","setting_word","double_act_or_scene"] #"dedication"

    long_front_elements = ["table_of_contents","list_of_illustrations","preface","introduction","character_list"]

    body_elements = ["prologue"]


    def find_title(self,feature_dict):
        last_title = 0
        for title_loc in feature_dict["title"]:
            if title_loc > 0 and title_loc in feature_dict["upper_case"] and title_loc -1 in feature_dict["blank_lines"] and title_loc +1 in feature_dict["blank_lines"]:
                if title_loc > last_title:
                    last_title = title_loc
        return last_title


    def get_front_score(self,feature_dict,loc,blanks,global_tags,start_index,end_index):
        score = 0
        score_dict = {}
        for feature_type in self.common_front_elements:
            if feature_type not in feature_dict or len(feature_dict[feature_type]) > 20:
                continue
            for index in feature_dict[feature_type]:
                if index < start_index or index >= end_index:
                    continue
                if index < loc:
                    score += 10
                    score_dict[feature_type] = score_dict.get(feature_type,0) + 1

        for feature_type in self.long_front_elements:
            if feature_type not in feature_dict or len(feature_dict[feature_type]) > 20:
                continue
            for index in feature_dict[feature_type]:
                if index < start_index or index >= end_index:
                    continue
                if index + 3 < loc:
                    score += 50
                    score_dict[feature_type] = score_dict.get(feature_type,0) + 1


        for feature_type in self.body_elements:
            if feature_type not in feature_dict or len(feature_dict[feature_type]) > 20:
                continue
            for index in feature_dict[feature_type]:
                if index < start_index or index >= end_index:
                    continue
                if index >= loc:
                    score += 20
                    score_dict[feature_type] = score_dict.get(feature_type,0) + 1
            

        for index in feature_dict["upper_case"]:
            if index < start_index or index >= end_index:
                continue
            if index < loc:
                score += 1
            

        if global_tags["Genre"] == "play":
            div_types = []#["act","text"]#,"scene"]
        else:
            div_types = ["chapter","book","part","text"]
        for div in div_types:
            chapter_dict = {}
            for index in feature_dict[div]:
                if feature_dict[div][index] == "?":
                    continue
                if index < start_index or index >= end_index:
                    continue
                if feature_dict[div][index] not in chapter_dict: 
                    chapter_dict[feature_dict[div][index]] = set()
                chapter_dict[feature_dict[div][index]].add(index)
            chapter_score = 0
            for chapter in chapter_dict:
                if len(chapter_dict[chapter]) >= 2:
                    if min(chapter_dict[chapter]) < loc <= max(chapter_dict[chapter]):
                        # head/body break should be between first (TOC) and last (text) instace of chapter, if possible
                        
                        if div == "text":
                            if start_index == 0: # only do this for main text:
                                score += 100
                        else:
                            score += 20
                        chapter_score += 1
                elif len(chapter_dict[chapter]) == 1:
                    #if there's only one, then front/body break should come before
                    if loc <= min(chapter_dict[chapter]):
                        chapter_score += 1
                        if div == "text":
                            if start_index == 0: # only do this for main text:
                                score += 100
                        else:
                            score += 20

        score -= feature_dict["not_front_lines"][loc]*2
        sys.stdout.flush()
        score += 10*min(blanks,3)
        return score


    def find_front(self,feature_dict,global_tags,start_index=None,end_index=None):
        if not start_index:
            start_index = 0
        if not end_index:
            end_index = feature_dict["total_length"]
        to_check = list(feature_dict["blank_set"])
        if not to_check:
            return 0
        to_check.sort(reverse=True)
        found_front = False
        i = 0
        best_loc = -1
        best_score = -9999
        while i < len(to_check):
            for index in feature_dict[to_check[i]]:
                if index < start_index or index >= end_index:
                    continue
                score = self.get_front_score(feature_dict,index,to_check[i], global_tags,start_index,end_index)
                
                if score > best_score:
                    best_score = score
                    best_loc = index
            i += 1


        title_loc = self.find_title(feature_dict)
        if title_loc > best_loc and (title_loc - start_index)/float(end_index - start_index) < 0.33:
            return title_loc
        else:
            return best_loc
    

    def remove_out_of_order(self,start,end,feature_dict,div_type):
        to_sort = []
        for index in feature_dict[div_type]:
            if start <= index < end:
                to_sort.append((index,feature_dict[div_type][index]))
        to_sort.sort()
        i = len(to_sort) - 1
        to_remove = set()
        while i >= 0 :
            if not (i == 0 or to_sort[i-1][1] == to_sort[i][1] - 1) or not (i == len(to_sort) -1  or to_sort[i+1][1] == to_sort[i][1] + 1):
                if i < 2 or to_sort[i-1][1] == to_sort[i][1] or not (to_sort[i-2][1] == to_sort[i][1] + 1): #next one looks better to delete
                    to_remove.add(to_sort[i][0])
                    to_sort = to_sort[:i] + to_sort[i+1:]
            i -= 1
        for index in to_remove:
            del feature_dict[div_type][index]
            
                                                                    

    def find_chapters_and_parts(self,front,back,feature_dict,start_lines,end_lines,plike_start,plike_end, global_tags):

        if global_tags["Genre"] == "play":
            div_types = ["act","scene"]
            self.remove_out_of_order(front,back,feature_dict,"act")
        elif global_tags["Genre"] == "poetry":
            return {}
        else:
            div_types = ["part","book","chapter"]
        done = set()
        spans = {}
        all_indicies = set()
        
        possible_default_closest_div = set()
        possible_default_closest_div.add(back)
        if feature_dict["the_end"] and max(feature_dict["the_end"])/float(feature_dict["total_length"]) > 0.90:
            possible_default_closest_div.add(max(feature_dict["the_end"]))

        if feature_dict["epilogue"]:
            possible_epilogues = filter( lambda x: front <= x < back and x/(back-front) > 0.90,feature_dict["epilogue"]) 
            if possible_epilogues:
                heading_tag = Tag(-1,-1,"head",None)
                heading_tag.plike = True
                div_tag = Tag(-1,-1,"epilogue",None)
                index = max(possible_epilogues)
                start_lines[index].append(div_tag)
                closest_div = min(filter(lambda x: x > index,possible_default_closest_div))
                end_lines[closest_div].append(div_tag)
                plike_start[index] = heading_tag
                plike_end[index+1] = heading_tag
                possible_default_closest_div.add(index)
                spans["epilogue"] = (index+1,closest_div)
            
        default_closest_div = min(possible_default_closest_div)
        
        for div_type in div_types:
            
            if div_type in feature_dict and len(feature_dict[div_type]) > 1:
                indicies = feature_dict[div_type].keys()
                indicies.sort()
                for index in indicies:
                    if index < front or (back and index >= back):
                        continue
                    else:
                        
                        closest_div = default_closest_div

                        if div_type == "chapter" or div_type == "scene":
                            for div_type2 in div_types:
                                
                                for possible in feature_dict[div_type2]:
                                    if possible > index and possible < closest_div and (div_type != div_type2 or feature_dict[div_type][index] != feature_dict[div_type2][possible]):
                                        closest_div = possible

                        else:

                            for possible in feature_dict[div_type]:
                                if possible > index and possible < closest_div and feature_dict[div_type][index] != feature_dict[div_type][possible]:
                                    closest_div = possible                            
                
                        i = 1
                        if  global_tags["Genre"] != "play":
                            while i < 4 and index + i not in feature_dict["chapter"] and (index +i in feature_dict["blank_lines"] or index +i + 1 in feature_dict["blank_lines"]):
                                i += 1

                        if closest_div - index < 10:
                            continue

                        all_indicies.add(index)
                        if div_type not in spans:
                            spans[div_type] = set()
                        spans[div_type].add((index+1,closest_div))


                        end_heading_index = index + i
                        heading_tag = Tag(-1,-1,"head",{"section":div_type})
                        heading_tag.plike = True
                        div_tag = Tag(-1,-1,"div",{"type":div_type,"n":feature_dict[div_type][index]})
                        start_lines[index].append(div_tag)
                        end_lines[closest_div].append(div_tag)
                        plike_start[index] = heading_tag
                        plike_end[end_heading_index] = heading_tag               

            else:
                pass
        if feature_dict["prologue"]:
            possible_prologues = filter( lambda x: front <= x < back and x/(back-front) < 0.10,feature_dict["prologue"]) 
            if possible_prologues:
                
                heading_tag = Tag(-1,-1,"head",None)
                heading_tag.plike = True
                div_tag = Tag(-1,-1,"prologue",None)
                index = min(possible_prologues)
                start_lines[index].append(div_tag)
                try:
                    closest_div = min(all_indicies)
                except:
                    closest_div = back
                end_lines[closest_div].append(div_tag)
                plike_start[index] = heading_tag
                plike_end[index+1] = heading_tag
                spans["prologue"] = (index+1,closest_div)
        if not spans:
            spans["text"] = set([(front,back)])
        return spans



    elements_mapping = {"dust_jacket":"div:dustjacket","year_only":"docDate","illustrated":"byLine","chapter":"contents","table_of_contents":"contents","dedication":"div:dedication", "introduction":"div:introduction","preface":"div:preface","publisher":"docImprint","by":"docTitle","year":"docImprint","illustration":"div:frontispiece","list_of_illustrations":"div:illustrations","quoted":"epigraph", "attribution":"epigraph","author":"docTitle","title":"docTitle","year":"docImprint","copy_right":"docImprint","city":"docImprint","series":"div:otherbooks","appendix":"div:appendix", "afterword":"div:afterword","endnotes":"div:endnotes","glossary":"div:glossary","bibliography":"div:bibliography","index":"div:index","character_list":"castList","performance":"performance","setting_word":"set","setting_phrase":"set","act":"contents", "the_end":"head"}

    weak_match = set(["dedication","quoted","year","by","attribution","city","performance"])
    strong_match = ["series","dust_jacket","year_only","illustrated","introduction","preface","publisher","title","author","copy_right","illustration","list_of_illustrations","chapter","appendix", "afterword","endnotes","glossary","bibliography","index","character_list","act", "setting_phrase","table_of_contents","the_end","setting_word"]
    multi_paragraph = set(["div:dustjacket","contents","div:introduction","div:preface","div:illustrations","div:otherbooks","div:appendix", "div:afterword","div:endnotes","div:glossary","div:bibliography","div:index","castList"])
    superceded = {"docTitle":set(["div:otherbooks","contents","castList","div:preface","div:introduction"]),"div:introduction":set(["contents"]),"div:preface":set(["contents"]),"docImprint":set(["performance"])}
    not_in_front = set(["div:appendix", "div:afterword","div:endnotes","div:glossary","div:bibliography","div:index"])
    not_in_back = set(["contents","div:introduction","div:preface","epigraph","div:frontispiece","castList","set"])

    def find_front_and_back_elements(self,local_start,local_end,front,back,feature_dict,start_lines,end_lines,plike_start,plike_end): 

        ranges = [(local_start,front,True)]
        if back:
            ranges.append((back,local_end,False))

        for bf_range in ranges:
            line_tag_list = {}
            weakly_tagged_line = set()
            for element in self.weak_match: # first do weak matches, extend to paragraph
                for index in feature_dict[element]:
                    if index < bf_range[0] or index > bf_range[1] or index in line_tag_list or (bf_range[2] and self.elements_mapping[element] in self.not_in_front) or (not bf_range[2] and self.elements_mapping[element] in self.not_in_back):
                        continue
                    line_tag_list[index] = self.elements_mapping[element]
                    weakly_tagged_line.add(index)
                    i = index + 1
                    while i not in feature_dict["blank_lines"] and i < bf_range[1]:
                        weakly_tagged_line.add(i)
                        line_tag_list[i] = self.elements_mapping[element]
                        i += 1

                    i = index - 1
                    while i not in feature_dict["blank_lines"] and i >= bf_range[0]:
                        weakly_tagged_line.add(i)
                        line_tag_list[i] = self.elements_mapping[element]
                        i -= 1
                        
            for element in self.strong_match: # then strong matches, same
                if self.elements_mapping[element] in self.multi_paragraph:
                    continue
                for index in feature_dict[element]:
                    if  index < bf_range[0] or index > bf_range[1] or (bf_range[2] and self.elements_mapping[element] in self.not_in_front) or (not bf_range[2] and self.elements_mapping[element] in self.not_in_back):
                        continue
                    if index in line_tag_list:
                        if line_tag_list[index] ==  self.elements_mapping[element]:
                            continue
                    line_tag_list[index] = self.elements_mapping[element]
                    weakly_tagged_line.discard(index)
                    i = index
                    while i not in feature_dict["blank_lines"] and i < bf_range[1]:
                        line_tag_list[i] = self.elements_mapping[element]
                        weakly_tagged_line.discard(i)
                        i += 1
                    i = index
                    while i not in feature_dict["blank_lines"] and i >= bf_range[0]:
                        line_tag_list[i] = self.elements_mapping[element]
                        weakly_tagged_line.discard(i)
                        i -= 1
            for element in self.strong_match: # then extend across paragraphs for multiparagraph elements
                if self.elements_mapping[element] in self.multi_paragraph:
                    for index in feature_dict[element]:
                        if index < bf_range[0] or index > bf_range[1] or (bf_range[2] and self.elements_mapping[element] in self.not_in_front) or (not bf_range[2] and self.elements_mapping[element] in self.not_in_back):
                            continue
                        if not index in feature_dict["upper_case"] and not ((index -1 in feature_dict["blank_lines"] or index == 0) and (index + 1 in feature_dict["blank_lines"])):
                            continue
                        i = index
                        while i not in feature_dict["blank_lines"] and i < bf_range[1]:
                            line_tag_list[i] = self.elements_mapping[element]
                            weakly_tagged_line.discard(i)
                            i += 1
                        if i == bf_range[1]:
                            continue
                        index = i - 1

                        next_para_index = None # go to next paragraph if multi_paragraph element
                        if index + 1 in feature_dict["blank_lines"]:
                            if index + 2 in feature_dict["blank_lines"] and index + 3 not in feature_dict["blank_lines"]:
                                next_para_index = index + 3
                            elif index + 2 not in feature_dict["blank_lines"]:
                                next_para_index = index + 2


                        if next_para_index:
                            while next_para_index not in feature_dict["blank_lines"] and next_para_index < bf_range[1]:
                                line_tag_list[next_para_index] = self.elements_mapping[element]
                                weakly_tagged_line.discard(next_para_index)
                                next_para_index += 1
            
 
                               
            last_line_tag = None
            blank_count = 0

            # for untagged lines, give most recent tag

            for i in range(bf_range[0],bf_range[1]):
                if i in line_tag_list:
                    
                    if last_line_tag in self.multi_paragraph and (blank_count <= 1 and (i in weakly_tagged_line or (line_tag_list[i] in self.superceded and last_line_tag in self.superceded[line_tag_list[i]]))):
                        line_tag_list[i] = last_line_tag
                        
                    last_line_tag = line_tag_list[i]
                else:
                    if last_line_tag:
                        line_tag_list[i] = last_line_tag
                if i in feature_dict["blank_lines"]:
                    blank_count += 1
                else:
                    blank_count = 0
                        
            current_tag = None
            current_start = 0

            # create tags
            for i in range(bf_range[0],bf_range[1]):
                if (i not in line_tag_list and i not in feature_dict["blank_lines"]):
                    continue
                if (i in line_tag_list and not current_tag) or (current_tag and i in line_tag_list and current_tag[0] != line_tag_list[i]):
                    if ":" in line_tag_list[i]:
                        main_tag,tag_type = line_tag_list[i].split(":")
                        new_tag =  Tag(-1,-1,main_tag,{"type":tag_type})
                    else:
                        new_tag =  Tag(-1,-1,line_tag_list[i],None)
                    new_tag.plike = True
                    if current_tag:
                        plike_end[i] = current_tag[1]
                    plike_start[i] = new_tag
                    current_tag = (line_tag_list[i],new_tag)
            if current_tag:
                plike_end[bf_range[1]] = current_tag[1]


    speaker_re_line = re.compile("^ *([^\(\[\r]+)(.+)")
    speaker_re_colon = re.compile("^ *([^\(\[\:]+)(.+)")
    speaker_re_period_cap = re.compile("^ *((?:[A-Z_\- ']+\.)+)(.+)")
    speaker_re_cap_only = re.compile("^ *((?:[A-Z_\- ']+)+)(.+)")
    speaker_re_period_nocap = re.compile("^ *([^\.\(\[]+\.)(.+)")


    def find_play_elements(self,sections,feature_dict,start_lines,end_lines,plike_start,plike_end,text_lines):
        sorted_features = []

        # need to figure out what indicates a line of dialogue
        for feature in ["starts_capitalized","early_period","early_colon","surrounded_by_underscore","start_with_parens","start_with_bracket","text_after_delim","short_line"]:
            if feature in feature_dict:
                sorted_features.append((len(feature_dict[feature]),feature))
        if not sorted_features:
            return
        sorted_features.sort(reverse=True)
        i = 1
        speaker_features = set([sorted_features[0][1]])
        no_line_between_speakers = sorted_features[0][0] > len(feature_dict["blank_lines"])
        while i < len(sorted_features) and sorted_features[i][1] != "start_with_parens" and sorted_features[i][1] != "start_with_bracket" and feature_dict[sorted_features[i][1]] and len(feature_dict[sorted_features[i-1][1]].intersection(feature_dict[sorted_features[i][1]]))/float(len(feature_dict[sorted_features[i-1][1]])) > 0.7:
            speaker_features.add(sorted_features[i][1])
            no_line_between_speakers = no_line_between_speakers and sorted_features[i][0] > len(feature_dict["blank_lines"])
            i += 1

        stage_features = set(["start_with_parens","start_with_bracket"])

        if "text_after_delim" not in speaker_features and "short_line" in speaker_features:
            speaker_separate_line = True
        else:
            speaker_separate_line = False

        set_count = 0
        for section in sections:
            seen_main = False
            has_set = False
            expecting_more = False
            current_tag = False
            last_speaker_start = 0
            last_speaker_end = 0
            last_stage_start = 0
            last_stage_end = 0
   
            for i in range(section[0],section[1]):
                if not seen_main: 
                    if i - 1 in feature_dict["blank_lines"] and not i in feature_dict["setting_word"] and ((has_most_features(i,speaker_features,feature_dict) and has_no_features(i,stage_features,feature_dict)) or (has_most_features(i,stage_features,feature_dict) and has_no_features(i,speaker_features,feature_dict))):
                        seen_main = True
                        if has_set:
                            new_tag =  Tag(-1,-1,"set",None)
                            set_count += 1
                            start_lines[section[0]].append(new_tag)
                            end_lines[i].append(new_tag)
                    else:
                        if i not in feature_dict["blank_lines"]:
                            has_set = True
                        continue

                is_speaker_line = has_most_features(i,speaker_features, feature_dict) 
                is_stage_line = has_most_features(i,stage_features, feature_dict) or (i in feature_dict["stage_word"] and i in feature_dict["starts_upper"])
                if not is_speaker_line and not is_stage_line:
                    if "starts_capitalized" in speaker_features and i in feature_dict["starts_capitalized"] and i in feature_dict["parens_after_capital"]:
                        is_speaker_line = True
                   
                if is_speaker_line and is_stage_line:
                    is_speaker_line = False

                if is_speaker_line and "text_after_delim" in speaker_features and i not in feature_dict["text_after_delim"]:
                    is_speaker_line = False


               # create actual tags



                if not i in feature_dict["blank_lines"]:

                    if expecting_more:
                       expecting_more = False

                    else:
                        if (i -1 in feature_dict["blank_lines"] or (no_line_between_speakers and ((is_speaker_line and i in feature_dict["text_after_delim"]) or is_stage_line))):
                            if is_speaker_line:
                                if current_tag:
                                    plike_end[i] = current_tag
                                    if current_tag.tag == "sp":
                                        last_speaker_end = i
                                    else:
                                        last_stage_end = i
                            
                                last_speaker_start = i
                                current_tag =  Tag(-1,-1,"sp",None)
                                current_tag.plike = True
                                plike_start[i] = current_tag
                                if speaker_separate_line:
                                    expecting_more = True

                            elif is_stage_line:
                                if current_tag:
                                    plike_end[i] = current_tag
                                    if current_tag.tag == "sp":
                                        last_speaker_end = i
                                    else:
                                        last_stage_end = i
                                last_stage_start = i
                                current_tag =  Tag(-1,-1,"stage",None)
                                current_tag.plike = True
                                plike_start[i] = current_tag
                                
                            else: 
                                if current_tag and current_tag.tag == "stage" and last_speaker_start:
                                    current_tag = plike_start[last_speaker_start]
                                    if last_speaker_end:
                                        del plike_end[last_speaker_end]                                        
                                    if last_stage_start > last_speaker_start and last_stage_end < last_stage_start:
                                        del plike_start[last_stage_start]
                        
            if current_tag:
                plike_end[section[1]] = current_tag

        # select re for distinguishing speaker and speech
        
        if "early_colon" in speaker_features:
            return self.speaker_re_colon

        elif speaker_separate_line:
            return self.speaker_re_line

        elif "starts_capitalized" in speaker_features:
            if "early period" in speaker_features:
                return self.speaker_re_period_cap
            else:
                return self.speaker_re_cap_only
        else:
            return self.speaker_re_period_nocap
        


    def find_back(self,feature_dict,front_index,global_tags,start_index=None,end_index=None):
        if not start_index:
            start_index = 0
        if not end_index:
            end_index = feature_dict["total_length"]
        total_length = end_index - start_index
        best_back = end_index
        max_back = end_index - int(total_length*0.3)

        if feature_dict["epilogue"]:
            for index in feature_dict["epilogue"]:
                if best_back > index > max_back and index in feature_dict["upper_case"]:
                    max_back = index + 10

        if feature_dict["chapter"]:
            for index in feature_dict["chapter"]:
                if best_back > index > max_back and index in feature_dict["upper_case"]:
                    max_back = index + 10

        if "curtain" in feature_dict and feature_dict["curtain"]:
            for index in feature_dict["curtain"]:
                if best_back > index > max_back and  index in feature_dict["upper_case"]:
                    max_back = index + 1

        has_definite_feature = False
        for feature in ["appendix","the_end","afterword","endnotes","glossary","bibliography","index","illustrations"]:
            if feature in feature_dict:
                for index in feature_dict[feature]:
                    if max_back < index < best_back:
                        has_definite_feature = True
                        if feature == "the_end":
                            best_back = index + 1
                        else:
                            best_back = index
        blank_count = 0
        if not has_definite_feature and not global_tags["Genre"] == "nonfiction":

            for i in range(max(max_back,end_index - 100),best_back):
                if i in feature_dict["blank_lines"]:
                    blank_count +=1
                else:
                    if blank_count == 4 and not (global_tags["Genre"] == "poetry"):
                        best_back = i
                        break
                    blank_count = 0

                if i in feature_dict["upper_case"] and (not global_tags["Genre"] == "play") and not (global_tags["Genre"] == "poetry"):
                    best_back = i
                    break

                        
        if best_back < end_index:
            return best_back
        else:
            return None
            
            
    def no_sent_tokenize(self,lines,start,end,tokens):
        sents = self.tokenizer.tokenize_span(" ".join(lines[start:end]).replace("  "," "))
        for sent in sents:
            tokens.extend(sent)   

    def paragraph_tokenize(self,lines,start,end,tokens,tags,paragraph_count,sentence_count):
        sents = self.tokenizer.tokenize_span(" ".join(lines[start:end]))
        para_start_index = len(tokens)
        sent_start_index = para_start_index
        for sent in sents:
            tokens.extend(sent)
            if sentence_count == 0:
                tags.append(Tag(sent_start_index,len(tokens),"s",None))
            else:
                tags.append(Tag(sent_start_index,len(tokens),"s",{"n":sentence_count}))
                sentence_count += 1
            sent_start_index = len(tokens)
        if paragraph_count == 0:
            tags.append(Tag(para_start_index,len(tokens),"p", None))
        else:
            tags.append(Tag(para_start_index,len(tokens),"p", {"n":paragraph_count}))
        
        return sentence_count

    def stanza_tokenize(self,lines,start,end,tokens,tags,stanza_tags,paragraph_count,sentence_count,depth):
        stanza_start_index = len(tokens)
        for i in range(start,end):
            sentence_count += 1
            line_start_index = len(tokens)
            new_lines = self.tokenizer.tokenize_span(lines[i])
            for line in new_lines:
                tokens.extend(line)
            tags.append(Tag(line_start_index,len(tokens),"l",{"n":sentence_count}))
            tags[-1].plike = True
            tags[-1].depth = depth + 2       
            sent_start_index = len(tokens)
        stanza_tags.append(Tag(stanza_start_index,len(tokens),"lg", {"type":"stanza", "n":paragraph_count}))
        stanza_tags[-1].depth = depth + 1
        return sentence_count

    def illustration_tokenize(self,lines,start,end,tokens,tags):
        span = " ".join(lines[start:end]).strip("\n []")
        span = span[span.find(":") + 1:]
        sents = self.tokenizer.tokenize_span(span)
        start_index = len(tokens)
        for sent in sents:
            tokens.extend(sent)
        tags.append(Tag(start_index,len(tokens),"illustration", None))


    def footnote_tokenize(self,lines,start,end,tokens,tags):
        span = " ".join(lines[start:end]).strip("\n []")
        num = span[span.find("ootnote") + 8:span.find(":")].strip()
        span = span[span.find(":") + 1:]
        sents = self.tokenizer.tokenize_span(span)
        start_index = len(tokens)
        for sent in sents:
            tokens.extend(sent)
        tags.append(Tag(start_index,len(tokens),"note", {"place":"bottom", "target":("#footnote" + num),"n":num}))

    def find_subtexts(self,text_lines,feature_dict):
        if feature_dict["table_of_contents"]:           
            header_index = min(feature_dict["table_of_contents"])
            content_lines = []
            if header_index in feature_dict["upper_case"] and header_index/float(feature_dict["total_length"]) < 0.1:
                i = header_index +1
                while i in feature_dict["blank_lines"] or i in feature_dict["ends_with_page"]:
                    i += 1
                while not (i in feature_dict["blank_lines"] and i + 1 in feature_dict["blank_lines"]):
                    if i in feature_dict["act"] or i in feature_dict["scene"] or i in feature_dict["chapter"] or i in feature_dict["part"] or i in feature_dict["book"] or i in feature_dict["starts_with_roman"] or i in feature_dict["blank_lines"]:
                        pass
                    else:       
                        content_lines.append(text_lines[i])
                    i+= 1

                start_search = i

                titles = []
                if content_lines:
                    for content_line in content_lines:
                        if "  " in content_line and content_line[content_line.rfind("  ") + 2:].isdigit():
                            titles.append(content_line[:content_line.rfind("  ")].strip().lower())
                        else:
                            titles.append(content_line.strip().lower())
                feature_dict["text"] = {}
                if titles > 1:
                    for i in range(start_search,len(text_lines)):
                        if i -1 in feature_dict["blank_lines"] and i + 1 in feature_dict["blank_lines"] and text_lines[i].lower() in titles:
                            text_index = titles.index(text_lines[i].lower())
                            feature_dict["text"][i] = text_index
                if len(feature_dict["text"]) == 1:
                    feature_dict["text"] = {}
            
     
    def find_break_cast_index(self,item):

        if "}" in item:
            return item.find("}")

        elif "(" in item:
            return item.find("(")

        elif "   " in item:
            return item.find("   ")

        elif 0 < item.count(",") < 3:
            return item.find(",")

        else:
            if item.isupper():
                return len(item)
            i = item.find(" ")
            best_so_far = 0
            while i != -1:
                if i > 3:
                    if item[:i].isupper():
                        best_so_far = i
                    else:
                        break
                i = item.find(" ", i+1)
            if best_so_far:
                return best_so_far
            else:
                return len(item)


    def is_drama_verse(self,span):
        all_capitalized = True
        one_definitive = False
        index = 0
        while index != -1:
            start = index
            while index < len(span) and not span[index].isalpha():
                index += 1
            if index < len(span) and not span[index].isupper():
                all_capitalized = False
                break
            else:
                if not one_definitive and index < len(span) and start > 0 and span[start-1] not in self.sent_punct:
                    one_definitive = True
            index = span.find("\r",index)
        return all_capitalized and one_definitive

    def is_verse(self,feature_dict,start,end):
        if end - start < 2:
            return False
        upper_count = 0
        lower_count = 0
        for i in range(start,end):
            if i in feature_dict["starts_upper"]:
                upper_count += 1
            elif i in feature_dict["starts_lower"]:
                lower_count += 1
        if (upper_count <= 3 and lower_count) or (upper_count > 3 and lower_count >= upper_count): #allow for occasional wrap arounds, etc.
            return False
        for i in range(start,end - 1):
            if i not in feature_dict["ends_with_sent_punct"] and i + 1 in feature_dict["starts_upper"]:
                return True
        return False


    def is_part_header(self,feature_dict,lines,line_num):
        return line_num in feature_dict["starts_with_roman"] or lines[line_num].strip().startswith("CANTO ")
    
    collection_indicators = re.compile("Plays|Novels|Poems|Works|Stories")
    stage_re =  re.compile("^([^\[\(]*)[\[\(]([^\]\)]+)[\]\)](.*)$")
    multiple_cast_split = re.compile(",|(\Wand(\W|$))")


    poetry_header_token_buffer = 50 # allow 50 tokens between poetry header and text

    def find_structure_and_tokenize(self,text_lines,global_tags):

        feature_dict = self.get_structural_features(text_lines,global_tags)
        if self.collection_indicators.search(global_tags["Title"][0]):
            self.find_subtexts(text_lines,feature_dict)
        if not "text" in feature_dict:
            feature_dict["text"] = set()
            
        tags = []
        plike_start_lines = {} #plike means are replacement for p, may require
        plike_end_lines = {}     #special tokenization/further decomposition
        start_lines = defaultdict(list)
        end_lines = defaultdict(list)
        if feature_dict["text"]:
            front_index = min(feature_dict["text"])
        else:
            front_index = self.find_front(feature_dict,global_tags)
        text_tag = Tag(-1,-1,"text",None)
        text_tag.depth = 0
        body_tag = Tag(-1,-1,"body",None)       
        body_tag.depth = 1
        if front_index:
            front_tag = Tag(-1,-1,"front",None)
            front_tag.depth = 1
            start_lines[0].append(front_tag)
            end_lines[front_index].append(front_tag)
            
        start_lines[0].append(text_tag)
        start_lines[front_index].append(body_tag)
        back_index = self.find_back(feature_dict,front_index,global_tags)
        if back_index:
            back_tag = Tag(-1,-1,"back",None)
            back_tag.depth = 1
            end_lines[back_index].append(body_tag)
            start_lines[back_index].append(back_tag)
            end_lines[len(text_lines)].append(back_tag)
        else:
            end_lines[len(text_lines)].append(body_tag)
        end_lines[len(text_lines)].append(text_tag)
        self.find_front_and_back_elements(0,len(text_lines),front_index,back_index,feature_dict,start_lines,end_lines,plike_start_lines,plike_end_lines)
        if not back_index:
            back_index = feature_dict["total_length"]
        if feature_dict["text"]:
            body_tag.tag = "group"
            breaks = []
            for index in feature_dict["text"]:
                if front_index <= index < back_index:
                    breaks.append(index)
                    feature_dict["title"].add(index)
            breaks.append(back_index)
            breaks.sort()
            section_spans = {}
            for i in range(len(breaks) - 1):
                text_tag = Tag(-1,-1,"text",None)
                text_tag.depth = 2
                body_tag = Tag(-1,-1,"body",None)
                body_tag.depth = 3
                start = breaks[i]
                end = breaks[i+1]
                start_lines[start].append(text_tag)
                local_front = self.find_front(feature_dict,global_tags,start_index=start,end_index=end)
                if local_front > start:
                    front_tag = Tag(-1,-1,"front",None)
                    front_tag.depth = 3
                    start_lines[start].append(front_tag)
                    end_lines[local_front].append(front_tag)

                start_lines[local_front].append(body_tag)
                local_back =  self.find_back(feature_dict,front_index,global_tags,start_index=start,end_index=end)
                if local_back:
                    back_tag = Tag(-1,-1,"back",None)
                    back_tag.depth = 3
                    end_lines[local_back].append(body_tag)
                    start_lines[local_back].append(back_tag)
                    end_lines[end].append(back_tag)
                else:
                    end_lines[end].append(body_tag)

                self.find_front_and_back_elements(start,end,local_front,local_back,feature_dict,start_lines,end_lines,plike_start_lines,plike_end_lines)
                
                if not local_back:
                    local_back = end
                end_lines[end].append(text_tag)
                temp_section_spans = self.find_chapters_and_parts(local_front,local_back,feature_dict,start_lines,end_lines,plike_start_lines,plike_end_lines,global_tags)
                for div in temp_section_spans:
                    if div not in section_spans:
                        section_spans[div] = set()
                    section_spans[div].update(temp_section_spans[div])
        else:
            section_spans = self.find_chapters_and_parts(front_index,back_index,feature_dict,start_lines,end_lines,plike_start_lines,plike_end_lines,global_tags)

        if global_tags["Genre"] == "poetry":
            poem_tag = None
            part_tag = None
            part_start_stanzas = 0
            stanzas = []
            parts = []

        if global_tags["Genre"] == "play":
            sections = set()
            if "scene" in section_spans:
                sections.update(section_spans["scene"])
            if "act" in section_spans:
                for act in section_spans["act"]:
                    has_scene = False
                    for scene in sections:
                        if scene[0] >= act[0] and scene[1] <= act[1]:
                            has_scene = True
                    if not has_scene:
                        sections.add(act)
            if "text" in section_spans:
                sections.update(section_spans["text"])
            speaker_re = self.find_play_elements(sections,feature_dict,start_lines,end_lines,plike_start_lines,plike_end_lines,text_lines)

           
        tokens = []
        start_line = 0
        sentence_count = 1
        paragraph_count = 1
        part_count = 0
        new_start = True
        in_plike = False
        depth = 0
        has_contents = False

        for i in range(len(text_lines) + 1):

            if i == front_index + 1 or i == back_index + 1:
                sentence_count = 1
                paragraph_count = 1
                
            if i in plike_end_lines:
                if plike_end_lines[i].tag == "div" and plike_end_lines[i].attributes["type"] in ["introduction","preface","dustjacket","afterword","appendix"]:
                    plike_end_lines[i].plike = False
                    at_head = True
                    seen_content = False
                    head_tag = Tag(len(tokens),-1,"head",None)
                    head_tag.depth = depth + 1
                    head_tag.plike = True
                    last_break = start_line
                    for j in range(start_line,i + 1):
                        if j == len(text_lines) or not text_lines[j] or j == i:
                            if at_head:
                                self.no_sent_tokenize(text_lines,last_break,j,tokens)
                                head_tag.end = len(tokens)
                                at_head = False
                                seen_content = False
                                last_break = j
                                tags.append(head_tag)
                            else:
                                if seen_content:
                                    if last_break in feature_dict["illustration"]:
                                        self.illustration_tokenize(text_lines,last_break,j,tokens,tags)
                                    elif last_break in feature_dict["footnote"]:
                                        self.footnote_tokenize(text_lines,last_break,j,tokens,tags)
                                    else:
                                        sentence_count = self.paragraph_tokenize(text_lines,last_break,j,tokens,tags,paragraph_count,sentence_count)
                                        paragraph_count += 1
                                    tags[-1].depth = depth + 1
                                    tags[-1].plike = True
                                    last_break = j
                                    seen_content = False
                            while last_break < len(text_lines) and not text_lines[last_break]:
                                last_break += 1
                                
                        else:
                            seen_content=True

                elif plike_end_lines[i].tag == "contents" or (plike_end_lines[i].tag == "div" and plike_end_lines[i].attributes["type"] == "illustrations") or (plike_end_lines[i].tag == "div" and plike_end_lines[i].attributes["type"] == "index"):
                    plike_end_lines[i].plike = False
                    item_index = set()
                    if plike_end_lines[i].tag == "contents":


                        # first look for likely divisions
                            
                        for div_type in ["chapter","part","book","wordnum_only","roman_only", "digit_only","starts_with_roman"]:
                            if div_type in feature_dict:
                                temp_index = set()
                                for index in feature_dict[div_type]:
                                    if start_line < index < i:
                                        temp_index.add(index)                          
                                if len(temp_index) > 1:
                                    item_index.update(temp_index)

                        for div_type in ["act","scene"]:
                            if div_type in feature_dict:
                                temp_index = set()
                                for index in feature_dict[div_type]:
                                    if start_line <= index < i:
                                        temp_index.add(index)                         
                                if len(temp_index) > 1:
                                    item_index.update(temp_index)

                        if len(item_index) > 2:
                            for feature in ["introduction","appendix","index","prologue","epilogue","preface","glossary","bibliography"]:
                                for index in feature_dict[feature]:
                                    if start_line < index < i:
                                        item_index.add(index)

                    # if not, just add all blank lines
                                
                    if not item_index or len(item_index) == 1:
                        temp_index = set()
                        for j in range(start_line+1,i-1):
                            if j in feature_dict["blank_lines"] and j +1 not in feature_dict["blank_lines"]:
                                temp_index.add(j+1)
                        if len(temp_index) > 2:
                            item_index.update(temp_index)
                    if len(item_index) == 0:
                        for j in range(start_line+1,i-1):
                            if j not in feature_dict["blank_lines"]: 
                                item_index.add(j)
                    elif len(item_index) == 1:
                        for j in range(item_index.pop(),i-1):
                            if j not in feature_dict["blank_lines"]: 
                                item_index.add(j)
                    item_index.difference_update(feature_dict["ends_with_page"])
                    if not item_index:
                        plike_end_lines[i].tag = "head"
                        plike_end_lines[i].depth = depth
                        plike_end_lines[i].plike = True
                        plike_end_lines[i].start = len(tokens)
                        self.no_sent_tokenize(text_lines,start_line,i,tokens)
                        plike_end_lines[i].end = len(tokens)
                    else:
                        item_index = list(item_index)
                        item_index.sort()
                        if start_line not in feature_dict["act"] and start_line not in feature_dict["scene"]:
                            head_tag = Tag(len(tokens),-1,"head",None)
                            head_tag.depth = depth + 1
                            head_tag.plike = True
                            self.no_sent_tokenize(text_lines,start_line,item_index[0],tokens)
                            head_tag.end = len(tokens)
                            tags.append(head_tag)
                        list_start = len(tokens)
                        for j in range(0,len(item_index) - 1):
                            item_tag = Tag(len(tokens),-1,"item",None)
                            item_tag.depth = depth + 2
                            item_tag.plike = True
                            self.no_sent_tokenize(text_lines,item_index[j],item_index[j+1],tokens)
                            item_tag.end = len(tokens)
                            tags.append(item_tag)
                        item_tag = Tag(len(tokens),-1,"item",None)
                        item_tag.depth = depth + 2
                        item_tag.plike = True
                        self.no_sent_tokenize(text_lines,item_index[-1],i,tokens)
                        item_tag.end = len(tokens)
                        tags.append(item_tag)
                        if plike_end_lines[i].tag == "contents":
                            list_tag = Tag(list_start,len(tokens),"list",{"type":"contents"})
                            has_contents = True
                        elif plike_end_lines[i].attributes["type"] == "illustrations":
                            list_tag = Tag(list_start,len(tokens),"list",{"type":"illustrations"})
                        elif plike_end_lines[i].attributes["type"] == "index":
                            list_tag = Tag(list_start,len(tokens),"list",{"type":"index"})
                        list_tag.depth = depth + 1
                        tags.append(list_tag)
                elif plike_end_lines[i].tag == "sp":

                    plike_end_lines[i].start = len(tokens)
                    plike_end_lines[i].plike = False
                    speaker_span = "\r".join(text_lines[start_line:i])
                    inserted_speaker = False

                    match = speaker_re.search(speaker_span)
                    if match:

                        the_rest = match.group(2).lstrip("._ ")
                        the_rest = the_rest.strip()
                        if the_rest:

                            speaker_tag = Tag(len(tokens),-1,"speaker",None)
                            speaker_tag.depth = depth + 1
                            speaker_tag.plike = True

                            sents = self.tokenizer.tokenize_span(match.group(1).strip(": .][()_"))
                            for sent in sents:
                                tokens.extend(sent)
                            
                            speaker_tag.end = len(tokens)
                            tags.append(speaker_tag)
                            inserted_speaker = True

                            if self.is_drama_verse(the_rest):
                                lg_tag = Tag(len(tokens),-1,"lg",None)
                                lg_tag.plike = False
                                lg_tag.depth = depth + 1
                                
                                the_rest = the_rest.split("\r\r")
                                for span in the_rest:
                                    match = self.stage_re.search(span)
                                    while match:
                                        speech = match.group(1)
                                        stage = match.group(2).strip("_ ")
                                        span = match.group(3).lstrip(". _")
                                        speech = speech.rstrip(" _\r").lstrip(":. _\r")
                                        if speech:
                                            verse_lines = speech.split("\r")
                                            for verse_line in verse_lines:
                                                sents = self.tokenizer.tokenize_span(verse_line)
                                                line_start_index = len(tokens)
                                                for sent in sents:
                                                    tokens.extend(sent)
                                                tags.append(Tag(line_start_index,len(tokens),"l",None))
                                                tags[-1].depth = depth + 2
                                                tags[-1].plike = True
                                        stage = stage.strip()
                                        stage_tag = Tag(len(tokens),-1,"stage",None)
                                        sents = self.tokenizer.tokenize_span(stage.replace("\r"," "))
                                        for sent in sents:
                                            tokens.extend(sent)
                                        stage_tag.end = len(tokens)
                                        stage_tag.depth = depth + 2
                                        stage_tag.plike = True
                                        tags.append(stage_tag)
                                        match = self.stage_re.match(span)
                                    span = span.strip()
                                    if "[" in span:
                                        stage_tag = Tag(len(tokens),-1,"stage",None)
                                        sents = self.tokenizer.tokenize_span(span[span.find("[")+1:].replace("\r"," "))
                                        for sent in sents:
                                            tokens.extend(sent)
                                        stage_tag.end = len(tokens)
                                        tags.append(stage_tag)
                                        span = span[:span.find("[")].rstrip()

                                    if span:
                                        verse_lines = span.split("\r")
                                        for verse_line in verse_lines:
                                            sents = self.tokenizer.tokenize_span(verse_line)
                                            line_start_index = len(tokens)
                                            for sent in sents:
                                                tokens.extend(sent)
                                            tags.append(Tag(line_start_index,len(tokens),"l",None))
                                            tags[-1].depth = depth + 2
                                            tags[-1].plike = True

                                lg_tag.end = len(tokens)
                                tags.append(lg_tag)   

                            else:                      
                                p_tag = Tag(len(tokens),-1,"p",None)
                                p_tag.plike = True
                                p_tag.depth = depth + 1
                                the_rest = the_rest.split("\r\r")
                                for span in the_rest:
                                    match = self.stage_re.search(span)
                                    while match:
                                        speech = match.group(1)
                                        stage = match.group(2).strip("_ ")
                                        span = match.group(3).lstrip(". _")
                                        speech = speech.rstrip(" _").lstrip(":. _")
                                        if speech:
                                            sents = self.tokenizer.tokenize_span(speech.replace("\r"," "))
                                            sent_start_index = len(tokens)
                                            for sent in sents:
                                                tokens.extend(sent)
                                                tags.append(Tag(sent_start_index,len(tokens),"s",None))
                                                sent_start_index = len(tokens)
                                        stage = stage.strip()
                                        stage_tag = Tag(len(tokens),-1,"stage",None)
                                        sents = self.tokenizer.tokenize_span(stage.replace("\r"," "))
                                        for sent in sents:
                                            tokens.extend(sent)
                                        stage_tag.end = len(tokens)
                                        tags.append(stage_tag)
                                        match = self.stage_re.match(span)
                                    span = span.strip()
                                    if "[" in span:
                                        stage_tag = Tag(len(tokens),-1,"stage",None)
                                        sents = self.tokenizer.tokenize_span(span[span.find("[")+1:].replace("\r"," "))
                                        for sent in sents:
                                            tokens.extend(sent)
                                        stage_tag.end = len(tokens)
                                        tags.append(stage_tag)
                                        span = span[:span.find("[")].rstrip()

                                    if span:
                                        sents = self.tokenizer.tokenize_span(span.replace("\r"," ").rstrip(" _").lstrip(":. _"))
                                        sent_start_index = len(tokens)
                                        for sent in sents:
                                            tokens.extend(sent)
                                            tags.append(Tag(sent_start_index,len(tokens),"s",None))
                                            sent_start_index = len(tokens)
                                p_tag.end = len(tokens)
                                tags.append(p_tag)

                    if not inserted_speaker: #fall back to stage if no speaker or speech
                        plike_end_lines[i].tag = "stage"
                        sents =self.tokenizer.tokenize_span(" ".join(text_lines[start_line:i]).strip(" ()_[]"))
                        for sent in sents:
                            tokens.extend(sent)
                        plike_end_lines[i].plike = True                       
                        

                elif plike_end_lines[i].tag == "stage":
                     sents =self.tokenizer.tokenize_span(" ".join(text_lines[start_line:i]).strip(" ()_[]"))
                     for sent in sents:
                        tokens.extend(sent)
                     plike_end_lines[i].plike = True
                    
                elif plike_end_lines[i].tag == "castList":
                    plike_end_lines[i].plike = False
                    head_tag = Tag(len(tokens),-1,"head",None)
                    head_tag.depth = depth + 1
                    head_tag.plike = True
                    self.no_sent_tokenize(text_lines,start_line,start_line + 1,tokens)
                    head_tag.end = len(tokens)
                    tags.append(head_tag)
                    
                    blank_count = 0.0
                    for j in range(start_line+2,i):
                        if j in feature_dict["blank_lines"] and j -1 not in feature_dict["blank_lines"] and j + 1 not in feature_dict["blank_lines"]:
                            blank_count += 1

                    j = start_line + 1
                    while j in feature_dict["blank_lines"]:
                        j += 1

                    castItems = []

                    last_start = j


                    if blank_count > 2 and blank_count/(i - (start_line+2)) > 0.25:
                        while j < i:
                            if j in feature_dict["blank_lines"] and j -1 not in feature_dict["blank_lines"] and j + 1 not in feature_dict["blank_lines"]:
                                castItems.append("\n".join(text_lines[last_start:j]))
                                last_start = j + 1
                            j += 1
                            
                    else:
                         while j < i:
                             if not j in feature_dict["blank_lines"]:
                                 castItems.append(text_lines[j])
                             j += 1


                    new_castItems = []
                    for castItem in castItems:                    
                         if castItem.count("}") > 1 and "\n" in castItem: 
                             new_castItems.extend(castItem.split("\n"))
                         elif castItem.strip().startswith("(") and new_castItems:
                             new_castItems[-1] += castItem
                         else:
                             new_castItems.append(castItem)
                    castItems = new_castItems
                    new_castItems = []
                    for item in castItems:
                         bracket_index = item.find("}")                
                         if bracket_index != -1 and self.multiple_cast_split.search(item[:bracket_index]):
                             roles = self.multiple_cast_split.split(item[:bracket_index])
                             for j in range(len(roles)):
                                 if roles[j] and roles[j].strip() and roles[j].strip() != "," and roles[j].strip() != "and" :
                                     if j == 0:
                                         new_castItems.append(roles[j].strip() + item[bracket_index - 1:])
                                     else:
                                         new_castItems.append(roles[j].strip() + " }")
                         else:
                             new_castItems.append(item)
                                     

                    castItems = new_castItems
                    temp_span = ""
                    start_multiple = -1

                    for j in range(len(castItems)):
                        if "}" in castItems[j]:                         
                            if start_multiple == -1:
                                start_multiple = j
                            if "{" in castItems[j]:
                                temp_span += castItems[j][castItems[j].find("}") + 1:castItems[j].find("{")] + " "
                            else:
                                temp_span += castItems[j][castItems[j].find("}") + 1:] + " "
                        else:
                            if start_multiple != -1:
                                while "  " in temp_span:
                                    temp_span = temp_span.replace("  "," ")
                                for k in range(start_multiple,j):
                                    if "{" in castItems[k]:
                                        castItems[k] = castItems[k][:castItems[k].find("}") + 1] + temp_span + castItems[k][castItems[k].find("{"):]
                                    else:
                                        castItems[k] = castItems[k][:castItems[k].find("}") + 1] + temp_span
                                start_multiple = -1
                                temp_span = ""
                        

                    for item in castItems:
                       item = item.strip()
                       item_tag = Tag(len(tokens),-1,"castItem",None)
                       item_tag.depth = depth + 1
                       break_index = self.find_break_cast_index(item)
                       role = item[:break_index].strip(" ,.")
                       roleDesc = item[break_index + 1:]
                       role_tag = Tag(len(tokens),-1,"role",None)
                       role_tag.depth = depth + 2
                       role_tag.plike = True
                       sents =self.tokenizer.tokenize_span(role)
                       for sent in sents:
                           tokens.extend(sent)
                       role_tag.end = len(tokens)
                       tags.append(role_tag)
                       roleDesc = roleDesc.strip("( .;_,):")
                       if roleDesc:
                            role_desc_tag = Tag(len(tokens),-1,"roleDesc",None)
                            role_desc_tag.depth = depth + 2
                            role_desc_tag.plike = True
                            sents =self.tokenizer.tokenize_span(roleDesc)
                            for sent in sents:
                                tokens.extend(sent)
                            role_desc_tag.end = len(tokens)
                            tags.append(role_desc_tag)
                          
                       item_tag.end = len(tokens)
                       tags.append(item_tag)                   
                    
                else:
                    self.no_sent_tokenize(text_lines,start_line,i,tokens)
                    plike_end_lines[i].plike = True
                plike_end_lines[i].end = len(tokens)
                plike_end_lines[i].depth = depth
                if i < len(text_lines) and text_lines[i]:
                    start_line = i
                    new_start = False
                else:
                    start_line = -1
                    new_start = True
                in_plike = False
                tags.append(plike_end_lines[i])

            
                
            elif i == len(text_lines) or (not text_lines[i] and not new_start and not in_plike):
                if i == start_line + 1 and start_line in feature_dict["upper_case"] and start_line not in feature_dict["illustration"]:
                    if global_tags["Genre"] == "poetry" and start_line not in feature_dict["title"]:
                        if part_tag:
                            if len(stanzas) > part_start_stanzas:
                                part_tag.end = len(tokens)
                                tags.append(part_tag)
                                part_tag = None
                            else:
                                part_tag = None
                        if poem_tag and self.is_part_header(feature_dict,text_lines,start_line):
                            part_count += 1
                            part_tag = Tag(len(tokens),-1,"lg",{"type":"part", "n":part_count})
                            part_tag.depth = depth + 1
                            part_start_stanza = len(stanzas)
                            
                        else:
                            paragraph_count = 0
                            sentence_count = 0
                            part_count = 0
                            if poem_tag:
                                if len(stanzas) > 0:
                                    if len(stanzas) > 1:
                                        tags.extend(stanzas)
                                    poem_tag.end = len(tokens)
                                    tags.append(poem_tag)
                                    poem_tag = None
                                    stanzas = []
                                else:
                                    if not len(tokens) - poem_token_start < self.poetry_header_token_buffer:
                                        poem_tag = None

                            if not poem_tag:
                                poem_tag = Tag(len(tokens),-1,"lg",{"type":"poem"})
                                poem_tag.depth = depth
                                poem_tag_start = len(tags)
                                poem_token_start = len(tokens)

                    head_tag = Tag(len(tokens),-1,"head",None)
                    head_tag.depth = depth
                    if global_tags["Genre"] == "poetry":
                        if len(stanzas) > 0:
                            head_tag.depth += 1
                        if part_tag:
                            head_tag.depth += 1
                    head_tag.plike = True
                    self.no_sent_tokenize(text_lines,start_line,i,tokens)
                    head_tag.end = len(tokens)
                    tags.append(head_tag)
  
                else:
                    if global_tags["Genre"] == "poetry":
                        if self.is_verse(feature_dict,start_line,i):
                            paragraph_count += 1
                            if not poem_tag:
                                 poem_tag = Tag(len(tokens),-1,"lg",None)
                                 poem_tag.depth = depth
                            else:
                                if len(stanzas) == 0:
                                    for j in range(poem_tag_start,len(tags)): # add depth to that came before stanza
                                        if tags[j].depth != 99:
                                            tags[j].depth += 1
                                    
                                
                            if part_tag:
                                temp_depth = depth + 1
                            else:
                                temp_depth = depth
                                
                            sentence_count = self.stanza_tokenize(text_lines,start_line,i,tokens,tags,stanzas,paragraph_count,sentence_count,temp_depth)
                            if i == feature_dict["total_length"] or i == back_index:
                                if len(stanzas) > 0:
                                    if len(stanzas) > 1:
                                        tags.extend(stanzas)
                                    poem_tag.end = len(tokens)
                                    tags.append(poem_tag)
     
                        else:
                            paragraph_count = 0
                            sentence_count = 0
                            part_count = 0
                            if poem_tag:
                                if part_tag:
                                    if len(stanzas) > part_start_stanzas:
                                        part_tag.end = len(tokens)
                                        tags.append(part_tag)
                                        part_tag = None
                                else:
                                    part_tag = None
                                if len(stanzas) > 0:
                                    if len(stanzas) > 1:
                                        tags.extend(stanzas)
                                    poem_tag.end = len(tokens)
                                    tags.append(poem_tag)
                                    poem_tag = None
                                    stanzas = []
                                else:
                                    if not len(tokens) - poem_token_start < self.poetry_header_token_buffer:
                                        poem_tag = None

                            if start_line in feature_dict["illustration"]:
                                self.illustration_tokenize(text_lines,start_line,i,tokens,tags)
                            elif start_line in feature_dict["footnote"]:
                                self.footnote_tokenize(text_lines,start_line,i,tokens,tags)
                            else:
                                sentence_count = self.paragraph_tokenize(text_lines,start_line,i,tokens,tags,paragraph_count,sentence_count)
                            tags[-1].depth = depth
                            tags[-1].plike = True


                                                
                    else:
                        if start_line in feature_dict["illustration"]:
                            self.illustration_tokenize(text_lines,start_line,i,tokens,tags)
                        elif start_line in feature_dict["footnote"]:
                            self.footnote_tokenize(text_lines,start_line,i,tokens,tags)

                        else:
                            sentence_count = self.paragraph_tokenize(text_lines,start_line,i,tokens,tags,paragraph_count,sentence_count)
                            paragraph_count += 1
                        tags[-1].depth = depth
                        tags[-1].plike = True
                new_start = True
            else:
                if text_lines[i] and new_start:
                    start_line = i
                    new_start = False

            if i in end_lines:
                end_lines[i].sort()
                for tag in end_lines[i]:
                    tag.end = len(tokens)
                    depth -= 1
                    tags.append(tag)

            if i in start_lines:
                start_lines[i].sort()
                for tag in start_lines[i]:
                    tag.start = len(tokens)
                    tag.depth = depth
                    depth += 1
            if i in plike_start_lines:
                start_line = i
                plike_start_lines[i].start = len(tokens)
                plike_start_lines[i].depth = depth
                in_plike = True
        text = Text(tokens,tags)
        return text



#general purpose lexical tagger based on regular expressions
    
class RegexTagger:
    def __init__(self,regex,tag_name):
        self.regex = regex
        self.name = tag_name
        
    def tag_span(self,tokens,start,end):
        new_tags = []
        for i in range(start,end):
            if self.regex.match(tokens[i]):
                 new_tags.append(Tag(i,i+1,self.name,None))
        return new_tags


# a tagger which tags using a lexicon, supports multiwords
class LexiconTagger:
            
    
    def __init__(self, lexicon, tag_name, attribute_name,tokenizer,case_sensitive=False):
        self.name = tag_name
        self.attribute = attribute_name
        self.lexicon = lexicon
        self.case_sensitive = case_sensitive
        if not case_sensitive:
            to_fix = []
            for word in lexicon:
                if not word.islower():
                    to_fix.append(word)
            for word in to_fix:
                try:
                    self.lexicon[word.lower()] = self.lexicon[word]
                    del self.lexicon[word]
                except:
                    self.lexicon.append(word.lower())
                    self.lexicon.remove(word)
                
            
        self.multiword_trie = {}
        for entry in lexicon:
            words = tokenizer.tokenize_span(entry)[0]
            if len(words) > 1:
                self.add_to_multiword_trie(words,entry)

                

    def add_to_multiword_trie(self,words,entry):     
        curr_trie = self.multiword_trie
        for i in range(len(words) - 1):
            if words[i] not in curr_trie:
                curr_trie[words[i]] = {}
            else:
                try:
                    curr_trie[words[i]].startswith("")
                    curr_trie[-1] = curr_trie[words[i]]
                    curr_trie[words[i]] = {}
                except:
                    pass
            curr_trie = curr_trie[words[i]]
        if words[-1] in curr_trie:
            curr_trie[-1] = entry
        else:
            curr_trie[words[-1]] = entry

    def match(self,tokens,start,end):
        i = start
        curr_trie = self.multiword_trie
        best_match = 0
        entry = None
        while True:
            if i == end:
                return best_match, entry
            if not self.case_sensitive and not tokens[i].islower():
                word = tokens[i].lower()
            else:
                word = tokens[i]
            if word not in curr_trie:
                return best_match, entry
            else:
                curr_trie = curr_trie[word]
                try:
                    curr_trie.startswith("")
                    return i + 1, curr_trie
                except:
                    if -1 in curr_trie:
                        best_match = i + 1
                        entry = curr_trie[-1]
                    
            i += 1



    def tag_span(self,tokens,start,end):
        i = start
        new_tags = []
        while i < end:
            if self.multiword_trie:
                match_len, lex_entry = self.match(tokens,i,end)
            else:
                lex_entry = None
            if lex_entry:
                if self.attribute:
                    new_tags.append(Tag(i,match_len,self.name,{self.attribute:self.lexicon[lex_entry]}))
                else:
                    new_tags.append(Tag(i,match_len,self.name,None))
                i += match_len
            else:
                if not self.case_sensitive and not tokens[i].islower():
                    word = tokens[i].lower()
                else:
                    word = tokens[i]

                if word in self.lexicon:
                    if self.attribute:
                        new_tags.append(Tag(i,i+1,self.name,{self.attribute:self.lexicon[word]}))
                    else:
                        new_tags.append(Tag(i,i+1,self.name,None))
                i += 1



        return new_tags
                    

                        
# tags names in the text, based on capitalization and frequency

class NameTagger():

    count_filter = 10
    max_name_length = 3

    def __init__(self,tokenizer):
        self.bad_names = set()
        for word in GenreClassifier.common_words:
            self.bad_names.add(word.title())
        for word in Tokenizer.base_abbreviations:
            if word.istitle():
                self.bad_names.add(word)

        self.gender_classifier = GenderClassifier()
        self.tokenizer = tokenizer



    def add_name_tags(self,text):
        names_count_dict = {}
        for tag in text.tags:
            if tag.tag == "s":
                in_name = False
                start_index = -1
                start = tag.start + 1
                if text.tokens[tag.start] == u'“' or text.tokens[tag.start] == u'‘':
                    start += 1
                for i in range(start, tag.end):
                    add_name = False
                    if text.tokens[i] and text.tokens[i].istitle():
                        if not in_name:
                            in_name = True
                            start_index = i
                        elif i - start_index == self.max_name_length:
                            add_name = True

                    else:
                        if in_name:
                            add_name = True
                    if add_name:
                        name = " ".join(text.tokens[start_index:i])
                        names_count_dict[name] = names_count_dict.get(name,0) + 1
                        in_name = False
        final_set = {}
        
        for name in names_count_dict:
            if names_count_dict[name] > self.count_filter and name not in self.bad_names:
                final_set[name] = self.gender_classifier.classify(name.split(" ")[0].lower())

        lex_tagger = LexiconTagger(final_set,"persName","gender",self.tokenizer,case_sensitive=True)
        for tag in text.tags:
            if tag.tag == "s":
                text.tags.extend(lex_tagger.tag_span(text.tokens,tag.start,tag.end))


# Tagger which tags said elements (speech in fiction and nonfiction. Finds
# nearest name and assigns it as speaker

class SaidTagger():

    punct = set([",",".","?","!"])

    def add_initial_said_tags(self,text):
        new_tags = []
        for tag in text.tags:
            if tag.tag == "p":
                 last_opening = None
                 for i in range(tag.start,tag.end):
                    if text.tokens[i] == u'“':
                        last_opening = i
                        seen_punct = False
                 
                    elif text.tokens[i] == u'”':
                        if last_opening and seen_punct:
                            new_tags.append(Tag(last_opening,i + 1,"said",{}))
                            last_opening = None
                            
                    elif last_opening and text.tokens[i] in self.punct:
                        seen_punct = True
        text.tags.extend(new_tags)
                            

    def add_speakers(self,text):
        text.tags.sort()
        current_p = None
        current_s = None
        closest_name = None
        i = 0
        while i < len(text.tags):
            tag = text.tags[i]
            if tag.tag == "p":
                current_p = tag
                i += 1
            elif tag.tag == "s":
                current_s = tag
                i += 1
            elif tag.tag == "persName":
                closest_name = tag
                i += 1
            elif tag.tag == "said":
                if current_s and closest_name and tag.start < current_s.end and closest_name.start > current_s.start:
                    prev_same_sent = True
                else:
                    prev_same_sent = False
                if current_p and closest_name and closest_name.start > current_p.start:
                    prev_same_para = True
                else:
                    prev_same_para = False
                if closest_name:
                    prev_distance = tag.start - closest_name.end
                else:
                    prev_distance = -1
                j = i + 1
                while j < len(text.tags) and not text.tags[j].start >= tag.end:
                    if text.tags[j].tag == "s":
                        current_s = text.tags[j]
                    j += 1
                next_name = None
                while j < len(text.tags) and text.tags[j].tag != "p" and text.tags[j].tag != "said" and not next_name:
                    if text.tags[j].tag == "persName":
                        next_name = text.tags[j]
                    else:
                        j += 1
                if next_name:
                    if not closest_name:
                        tag.add_attribute("who","_".join(text.tokens[text.tags[j].start:text.tags[j].end]))
                    if current_s.start < tag.end and current_s.end > next_name.start:
                        next_same_sent = True
                    else:
                        next_same_sent = False
                    next_distance = text.tags[j].start - tag.end
                    if prev_same_sent and not next_same_sent:
                        tag.add_attribute("who","_".join(text.tokens[closest_name.start:closest_name.end]))
                    elif next_same_sent and not prev_same_sent or next_distance < prev_distance:
                        tag.add_attribute("who","_".join(text.tokens[text.tags[j].start:text.tags[j].end]))
                    elif closest_name:
                        tag.add_attribute("who","_".join(text.tokens[closest_name.start:closest_name.end]))
                else:
                    if closest_name:
                        tag.add_attribute("who","_".join(text.tokens[closest_name.start:closest_name.end]))
                
                i = j
            else:
                i += 1
                        
    def add_said_tags(self,text):
        self.add_initial_said_tags(text)
        self.add_speakers(text)


class FootnoteTagger:

    def add_footnote_tags(self,text):
        new_tags = []
        for i in range(1, len(text.tokens) - 1):
            if text.tokens[i].isdigit() and  text.tokens[i-1] == '[' and text.tokens[i+1] == ']':
                new_tags.append(Tag(i-1, i+2,"anchor",{"xml:id":"footnote" + text.tokens[i]}))
        text.tags.extend(new_tags)
    

# the basic lexicalized NLPUtil POS tagger. Fast and simple
        
class SimplePOSTagger():
    
  def __init__(self):
        lexHash = {}      
        upkl = open('resources/pickledlexicon', 'r')
        self.lexHash = cPickle.load(upkl)
        upkl.close()

  def tag(self,words):
            ret = []
            for i in range(len(words)):
                ret.append("NN")

                if words[i] in self.lexHash:
                        ret[i] = self.lexHash[words[i]]
                elif self.lexHash.has_key(words[i].lower()):
                        ret[i] = self.lexHash[words[i].lower()]
    
    #apply transformational rules
            for i in range(len(words)):
                #rule 1 : DT, {VBD | VBP} --> DT, NN
                if i > 0 and ret[i-1] == "DT":
                        if ret[i] == "VBD" or ret[i] == "VBP" or ret[i] == "VB":
                                ret[i] = "NN"
                                
                #rule 2: convert a noun to a number (CD) if "." appears in the word
                if ret[i].startswith("N"):
                        if words[i].find(".") > -1:
                                ret[i] = "CD"
                
                # rule 3: convert a noun to a past participle if ((string)words[i]) ends with "ed"
                if ret[i].startswith("N") and words[i].endswith("ed"):
                        ret[i] = "VBN"

                # rule 4: convert any type to adverb if it ends in "ly"
                if words[i].endswith("ly"):
                        ret[i] = "RB"
                        
                # rule 5: convert a common noun (NN or NNS) to a adjective if it ends with "al"
                if ret[i].startswith("NN") and words[i].endswith("al"):
                        ret[i] = "JJ"
                        
                # rule 6: convert a noun to a verb if the preceeding work is "would"
                if i > 0 and ret[i].startswith("NN") and words[i - 1].lower() == "would":
                        ret[i] = "VB"
                
                # rule 7: if a word has been categorized as a common noun and it ends with "s",
                # then set its type to plural common noun (NNS)
                if ret[i] == "NN" and words[i].endswith("s"):
                        ret[i] = "NNS"
                
                # rule 8: convert a common noun to a present prticiple verb (i.e., a gerand)
                if ret[i].startswith("NN") and words[i].endswith("ing"):
                        ret[i] = "VBG"
                        
            return ret

'''  Left out of this version due to speed
class NLTKPOSTagger:

    def __init__(self):
        pass

    def tag(self,words):
        return [temp[1] for temp in pos_tag(words)]       


class NLTKLemmatizer:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()

    def lemmatize(self,word):
        lemma = word
        if lemma.endswith("er") or word.endswith("est"):
            lemma = self.lemmatizer.lemmatize(lemma,'a')
        if lemma == word:
            lemma = self.lemmatizer.lemmatize(word,'v')
            if lemma == word:
                lemma = self.lemmatizer.lemmatize(word,'n')
        return lemma


    def lemmatize_all(self,tokens):
        lemma_tokens = []
        for token in tokens:
            lemma_tokens.append(self.lemmatize(token))
        return lemma_tokens
'''

class LemmatizerSimple:
    def __init__(self):
        f = open("resources/lemma_dict.dat","rb")
        self.lemma_lookup = cPickle.load(f)
        f.close()

    def lemmatize(self,word):
        if not word.islower():
            word = word.lower()
        if word in self.lemma_lookup:
            return self.lemma_lookup[word]
        else:
            return word

    def lemmatize_all(self,tokens):
        lemma_tokens = []
        for token in tokens:
            lemma_tokens.append(self.lemmatize(token))
        return lemma_tokens
  

# This class deals with all lexical tagging

class LexicalTagger:

    def __init__(self,options,tokenizer):
        self.options = options
        self.name_tagger = NameTagger(tokenizer)
        self.said_tagger = SaidTagger()
        if "tagged" in self.options and self.options["tagged"]:
            #if not standalone and self.options["tagger"] == "NLTK":
            #    self.pos_tagger = NLTKPOSTagger()
            #else:
            self.pos_tagger = SimplePOSTagger()

        self.internal_taggers = {}

        year_tagger = RegexTagger(StructureTagger.year,"date")
        city_tagger = LexiconTagger(StructureTagger.cities,"place",None,tokenizer)
        self.footnote_tagger = FootnoteTagger()
        country_tagger = LexiconTagger(StructureTagger.countries,"place",None,tokenizer)
        self.internal_taggers["docImprint"] = [year_tagger,city_tagger,country_tagger]
        self.internal_taggers["docDate"] = [year_tagger]
        

        self.selected_taggers = []
        self.selected_lemma_taggers = []
        if "lexical_tags" in self.options:
            for lexical_tag in self.options["lexical_tags"]:
                attribute = None
                stuff = lexical_tag.split("|")
                if stuff[0] == "user_lexicons":
                    f = codecs.open("user_lexicons/" + stuff[1] + ".txt",encoding="utf-8")
                    lexicon = []
                    name = stuff[1]
                    for line in f:
                        lexicon.append(line.strip())
                    f.close()
                    if "\t" in lexicon[0]:
                        attribute = "value"
                        new_lexicon = {}
                        for item in lexicon:
                            pair = item.split("\t")
                            try:
                                pair[1] = float(pair[1])
                            except:
                                pass
                            new_lexicon[pair[0]] = pair[1]
                        lexicon = new_lexicon

                else:
                    if stuff[0] != "GI":
                        attribute = "value"
                    f = codecs.open("built_in_lexicons/" + stuff[0] + ".txt",encoding="utf-8")
                    headings = f.readline().strip().split("\t")
                    index = headings.index(stuff[1])
                    
                    name = stuff[1]
                    if stuff[0] != "GI":
                        lexicon = {}
                        for line in f:
                            line = line.split("\t")
                            try:
                                line[index] = float(line[index])
                            except:
                                line[index] = line[index].strip()
                            if line[index]:
                                lexicon[line[0]] = line[index]
                    else:
                        lexicon = []
                        for line in f:
                            line = line.strip().split("\t")
                            if line[index]:
                                lexicon.append(line[0])
                        
                    
                if stuff[-2] == "casesens":
                    case_sense = True
                else:
                    case_sense = False
                tagger = LexiconTagger(lexicon,name,attribute,tokenizer,case_sense)
                if stuff[-1] == "lem":
                    self.selected_lemma_taggers.append(tagger)
                else:
                    self.selected_taggers.append(tagger)                
        
        if ("lemma" in self.options and self.options["lemma"] == True) or self.selected_lemma_taggers:
            #if standalone:
            self.lemmatizer = LemmatizerSimple()
            #else:
                #self.lemmatizer = Lemmatizer()

    def do_internal_tagging(self,text):
        new_tags = []
        for tag in text.tags:
            if tag.tag in self.internal_taggers:
                for tagger in self.internal_taggers[tag.tag]:
                    new_tags.extend(tagger.tag_span(text.tokens,tag.start,tag.end))

        return new_tags 

    def do_lexical_tagging(self,text,tag_dict):
        text.tags.extend(self.do_internal_tagging(text))

        self.footnote_tagger.add_footnote_tags(text)
        
        if tag_dict["Genre"] == "fiction":
            self.name_tagger.add_name_tags(text)
            self.said_tagger.add_said_tags(text)

        for tagger in self.selected_taggers:
            text.tags.extend(tagger.tag_span(text.tokens,0,len(text.tokens)))
        

        if self.selected_lemma_taggers or ("lemma" in self.options and self.options["lemma"]):
            lemma_tokens = self.lemmatizer.lemmatize_all(text.tokens)

            
        for tagger in self.selected_lemma_taggers:
           text.tags.extend(tagger.tag_span(lemma_tokens,0,len(lemma_tokens))) 

        if "tagged" in self.options and self.options["tagged"]:
            pos_tags = self.pos_tagger.tag(text.tokens)
            if "lemma" in self.options and self.options["lemma"]:
                text.tokens = lemma_tokens
            for i in range(len(text.tokens)):
                text.tokens[i] = "%s/%s" % (text.tokens[i],pos_tags[i])
        elif "lemma" in self.options and self.options["lemma"]:
            text.tokens = lemma_tokens
        return text
 

TEI_header_template = u''' <teiHeader>
  <fileDesc>
   <titleStmt>
    <title>**TITLE OF TEXT**</title>
    <author>**AUTHOR OF TEXT**</author>
    <respStmt>
     <resp>TEI generated by GutenTag v**version num** (http://www.cs.toronto.edu/~jbrooke/gutentag)</resp>
     <resp>Source text from Project Gutenberg (http://www.gutenberg.org)</resp>
    </respStmt>
   </titleStmt>
   <publicationStmt>
    <distributor>GutenTag</distributor>
    <availability>
     <p>GutenTag claims no copyright over this text, which is derived from a text from Project Gutenberg. The standard Project Gutenberg statement follows:</p>
     <p>This eBook is for the use of anyone anywhere at no cost and with almost no restrictions whatsoever.  You may copy it, give it away or re-use it under the terms of the Project Gutenberg License included at www.gutenberg.org</p>
    </availability>
   </publicationStmt>
   <sourceDesc>
    <biblStruct>
     <monogr>
      <author>
       <forename>**AUTHOR FIRST NAME**</forename>
       <surname>**AUTHOR LAST NAME**</surname> 
       <sex>**AUTHOR GENDER, M or F or NA**</sex>
       <birth>
        <date>**AUTHOR BIRTH DATE, IN FORMAT YYYY-MM-DD**</date>
        <country>**COUNTRY OF AUTHOR BIRTH**</country>
        <settlement>**CITY/TOWN OF AUTHOR BIRTH**</settlement>
       </birth>
       <death>
        <date>**AUTHOR DEATH DATE, IN FORMAT YYYY-MM-DD**</date>
        <country>**COUNTRY OF AUTHOR DEATH**</country>
        <settlement>**CITY/TOWN OF AUTHOR DEATH**</settlement>
       </death>
      </author>
      <title>**TITLE OF TEXT**</title>
      <imprint>
       <pubPlace>
        <country>**COUNTRY WHERE TEXT WAS PUBLISHED**</country>
        <settlement>**CITY WHERE TEXT WAS PUBLISHED**</settlement>
       </pubPlace>
       <publisher>**NAME OF PUBLISHER**</publisher>
       <date>**YEAR OF PUBLICATION**</date>
      </imprint>
     </monogr>
    </biblStruct>
   </sourceDesc>
  </fileDesc>
  <profileDesc>
   <langUsage>
    <language ident="**2-letter language code**">**SPELL OUT LANGUAGE NAME**</language>
   </langUsage>
   <textClass>
    <keywords scheme="#lcsh">
     <term>**LOC SUBJECT KEYWORD**</term>
    </keywords>
    <classCode scheme="#lc">**LOC CODE**</classCode>
   </textClass>
  </profileDesc>
 </teiHeader>
'''

header_pairs = [["**TITLE OF TEXT**","Title"],["**AUTHOR OF TEXT**","Author"],["**AUTHOR BIRTH DATE, IN FORMAT YYYY-MM-DD**","Author Birth"],["**AUTHOR DEATH DATE, IN FORMAT YYYY-MM-DD**","Author Death"],["**AUTHOR FIRST NAME**","Author Given"],["**AUTHOR LAST NAME**","Author Surname"],["**COUNTRY WHERE TEXT WAS PUBLISHED**","Publication Country"],["**YEAR OF PUBLICATION**","Publication Date"],["**LOC CODE**","LoC Class"],["**SPELL OUT LANGUAGE NAME**", "Language"]]

blanks = ["**NAME OF PUBLISHER**","**CITY WHERE TEXT WAS PUBLISHED**","**CITY/TOWN OF AUTHOR DEATH**","**COUNTRY OF AUTHOR DEATH**","**CITY/TOWN OF AUTHOR BIRTH**","**COUNTRY OF AUTHOR BIRTH**"]

language_lookup = {"English":"en","French":"fr","German":"de","Spanish":"es","Chinese":"zh","Dutch":"nl","Italian":"it","Japanese":"ja","Danish":"da","Norweigan":"no","Swedish":"sv","Finnish":"fi"}

def output_header(fout, tag_dict):

    TEI_header = TEI_header_template.replace("**version num**",version)
    for pair in header_pairs:
        if pair[1] in tag_dict and tag_dict[pair[1]]:
            if pair[1] == "Publication Date":
                TEI_header = TEI_header.replace(pair[0],tag_dict[pair[1]])
            elif "Birth" in pair[1] or "Death" in pair[1]:
                TEI_header = TEI_header.replace(pair[0],str(tag_dict[pair[1]][0]))
            else:
                TEI_header = TEI_header.replace(pair[0],tag_dict[pair[1]][0])
        else:
            blanks.append(pair[0])
    for blank in blanks:
        TEI_header = TEI_header.replace(blank,"")
    if "Author Gender" in tag_dict and tag_dict["Author Gender"]:
        if tag_dict["Author Gender"][0] == 'male':
            TEI_header = TEI_header.replace("**AUTHOR GENDER, M or F or NA**","M")
        else:
            TEI_header = TEI_header.replace("**AUTHOR GENDER, M or F or NA**","F")
    else:
        TEI_header = TEI_header.replace("**AUTHOR GENDER, M or F or NA**","NA")
    if tag_dict["Language"][0] in language_lookup:
        TEI_header = TEI_header.replace("**2-letter language code**",language_lookup[tag_dict["Language"][0]])
    else:
        TEI_header = TEI_header.replace("**2-letter language code**", "en")
        
    if "Subject" in tag_dict and tag_dict["Subject"]:
        subjects = "".join(["     <term>%s</term>\n" % subject for subject in tag_dict["Subject"]])
        TEI_header = TEI_header.replace("     <term>**LOC SUBJECT KEYWORD**</term>\n",subjects)        
    else:
        TEI_header = TEI_header.replace("     <term>**LOC SUBJECT KEYWORD**</term>\n","")
        
        
    fout.write(TEI_header)
  

# this function is needed to create valid XML tags out of GutenTag's representation
# which allows for overlapping tags
def split_overlapping_tags(text):
    new_tags = []
    end_indicies = {}
    start_indicies = {}
    tag_loc = 0
    split_count = 0
    text.tags.sort()
    for i in range(len(text.tokens) + 1):
        last_split_count = split_count
        if i in end_indicies:
            starts = []

            for tag in end_indicies[i]:
                starts.append(tag.start)

                start_indicies[tag.start].remove(tag)
                if not start_indicies[tag.start]:
                    del start_indicies[tag.start]

            del end_indicies[i]

            first_start = min(starts)
            for j in start_indicies.keys():
                if j > first_start and j != i:
                    for tag in start_indicies[j]:
                        if not (tag.attributes and "id" in tag.attributes):
                            if not tag.attributes:
                                tag.attributes = {}
                            tag.attributes["id"] = split_count
                            split_count += 1
                        new_attributes = {}
                        for item in tag.attributes:
                            new_attributes[item] =  tag.attributes[item]

                        next_id = tag.attributes["id"] 
                        prev_id = split_count
                        split_count += 1
                        tag.attributes["prev"] = prev_id
                        new_attributes["next"] = next_id
                        new_attributes["id"] = prev_id
                        new_tag = Tag(tag.start,i,tag.tag,new_attributes)
                        new_tag.depth = tag.depth 
                        tag.start = i
                        if i not in start_indicies:
                            start_indicies[i] = []
                        start_indicies[i].append(tag)
                        new_tags.append(new_tag)
                    del start_indicies[j]
                        

        while tag_loc < len(text.tags) and i == text.tags[tag_loc].start:
            if text.tags[tag_loc].end not in end_indicies:
                end_indicies[text.tags[tag_loc].end] = []
            end_indicies[text.tags[tag_loc].end].append(text.tags[tag_loc])
            if text.tags[tag_loc].start not in start_indicies:
                start_indicies[text.tags[tag_loc].start] = []
            start_indicies[text.tags[tag_loc].start].append(text.tags[tag_loc])
            tag_loc += 1
    text.tags.extend(new_tags)


def remove_useless_tags(tags,options):  #this prevents display bug
    not_wanted = []
    for i in range(len(tags)):
        tag = tags[i]
        if tag.get_single_tag() in options["not_display_tags"] and not tag.get_single_tag() in options["not_wanted_tags"]:
            not_wanted.append(i)
    not_wanted.sort(reverse=True)
    for index in not_wanted:
        del tags[index]


# wanted_tags : tags that have been explicitly selected for inclusions
# not_wanted_tags : tags that have explicitly selected to not be included
# not_display_tags: tags that are not visible
# (if output_format == "plain", all tags are not_display_tags



def display(tag,options):
    if options["output_format"] == "plain":
        return False
    elif tag.get_single_tag() in options["not_display_tags"]:
        return False
    return True

def check_tag_path(tag_path,options,genre):
    for i in range(len(tag_path) -1, -1,-1):
        if tag_path[i] + "|" +genre in options["wanted_tags"]:
            return True
        elif tag_path[i] + "|" +genre in options["not_wanted_tags"]:
            return False
        elif tag_path[i] in options["wanted_tags"]:
            return True
        elif tag_path[i] in options["not_wanted_tags"]:
            return False
    return True   

def add_to_tag_path(tag,tag_path,options,genre):
    tag_path.append(tag.get_single_tag())
    return check_tag_path(tag_path,options,genre)


def remove_from_tag_path(tag_path,options,genre):
    tag_path.pop()
    return check_tag_path(tag_path,options,genre)

# outputs a string (TEI or tokens) from a internet Text representation              
def output_text(text,fout,options,tag_dict):
    if "fiction" in tag_dict["Genre"]:
        genre = "prose"
    else:
        genre = tag_dict["Genre"]
    if options["output_format"] == "plain":
        if not "not_wanted_tags" in options or not options["not_wanted_tags"]:
            fout.write(" ".join(text.tokens))
            return len(text.tokens) > 0
    else:
        remove_useless_tags(text.tags,options)
        try:
            split_overlapping_tags(text)
        except:
            print tag_dict  # there's a bug here that needs to be fixed
    span_start = 0
    end_indicies = {}
    start_indicies = {}
    tag_loc = 0

    text.tags.sort()
    last_tagged_token = 0
    split_id = 1
    tag_path = []
    output_elements = True
    outputted_tokens = False
    for i in range(len(text.tokens) + 1):
        split_count = 0
        if i in end_indicies:
            end_indicies[i].reverse()
            if output_elements:
                outputted_tokens = True
                fout.write(" ".join(text.tokens[last_tagged_token:i]))
            last_tagged_token = i
            for tag in end_indicies[i]:
                if output_elements and display(tag,options):
                    if not tag.plike and tag.depth != 99:
                        fout.write(" "*(tag.depth + 1))
                    fout.write(tag.get_end_tag())
                    if tag.depth != 99:
                        fout.write("\n")
                output_elements = remove_from_tag_path(tag_path,options,genre)
                start_indicies[tag.start].remove(tag)
            del end_indicies[i]
                
        while tag_loc < len(text.tags) and i == text.tags[tag_loc].start:
            if text.tags[tag_loc].end not in end_indicies:
                end_indicies[text.tags[tag_loc].end] = []
            end_indicies[text.tags[tag_loc].end].append(text.tags[tag_loc])
            if text.tags[tag_loc].start not in start_indicies:
                start_indicies[text.tags[tag_loc].start] = []
            start_indicies[text.tags[tag_loc].start].append(text.tags[tag_loc])
            if output_elements:
                outputted_tokens = True
                fout.write(" ".join(text.tokens[last_tagged_token:i]))
            output_elements = add_to_tag_path(text.tags[tag_loc],tag_path,options,genre)
            last_tagged_token = i
            if output_elements and display(text.tags[tag_loc],options):
                if text.tags[tag_loc].depth != 99:
                    fout.write(" "*(text.tags[tag_loc].depth + 1))            
                fout.write(text.tags[tag_loc].get_start_tag())
                #fout.write(" " + str(text.tags[tag_loc].start) + " " + str(text.tags[tag_loc].end) + " ")
                if text.tags[tag_loc].depth != 99 and not text.tags[tag_loc].plike:
                    fout.write("\n")
            tag_loc += 1

    return outputted_tokens

           
# class for tagging an individual text

class GutenTextTagger:

    cities = ["London","New York","Oxford","Cambridge","Boston","Philadelphia","San Francisco","Toronto","Los Angeles","Chicago","Sydney","Auckland"]
    countries = ["U.S.A","U.S.","United States","United States of America","America","Canada","England","Britan","United Kingdom", "U.K.", "Australia", "New Zealand"]

    place_mappings = {"dublin":"IR","london":"UK","new york":"US","oxford":"UK","cambridge":"UK","boston":"US","philadelphia":"US","san francisco":"US","toronto":"CAN","los angeles":"US","chicago":"US","sydney":"AUS","auckland":"NZ","USA":"US","U.S.A":"US", "united states":"US","america":"US","canada":"CAN","england":"UK","ireland":"IR","britain":"UK","united kingdom":"UK", "u.k.":"UK", "australia":"AUS", "new zealand":"NZ"}

    def __init__(self,options):
        self.text_cleaner = TextCleaner()
        if options["mode"] == "tag_genres_and_get_pub_info":
            self.genre_classifier = GenreClassifier("genre_decision_tree.txt")
        tokenizer = Tokenizer()
        self.structure_tagger = StructureTagger(options,tokenizer)
        self.lexical_tagger =  LexicalTagger(options,tokenizer)
        self.options = options



    def process_text(self,tag_dict):
        start = time.time()
        href = tag_dict["href"]
        charset = tag_dict["charset"]
        print href
        try:
            my_zip = zipfile.ZipFile(self.options["corpus_dir"] + href.upper())
            if not my_zip.namelist()[0].endswith(".txt"):
                return None,tag_dict
            f = my_zip.open(my_zip.namelist()[0])
            raw_text = f.read().decode(charset)
        except:
            print "fail"
            return None,tag_dict
        f.close()
        load_time = time.time() - start               
        start = time.time()
        cleaned_text = self.text_cleaner.clean_text(raw_text)
        clean_time = time.time() - start
        text_restrictions = self.options["subcorpus" + str(tag_dict["subcorpus"]) + "_restrictions"]
        if "lexical_restrictions" in text_restrictions:
            for phrase in text_restrictions["lexical_restrictions"]:
                if phrase not in cleaned_text:
                    return None,tag_dict
        cleaned_text = cleaned_text.splitlines()
        if self.options["mode"] == "genre_training":
            tag_dict["genre_features"] = self.genre_classifier.get_feature_dict(cleaned_text,tag_dict)
        elif self.options["mode"] == "tag_genres_and_get_pub_info":
            tag_dict["Genre"] =  self.genre_classifier.classify_genre(cleaned_text,tag_dict)
            
        text = self.structure_tagger.find_structure_and_tokenize(cleaned_text,tag_dict)
            
        text = self.lexical_tagger.do_lexical_tagging(text,tag_dict)           

        if self.options["mode"] == "tag_genres_and_get_pub_info":
            dates = set()
            countries = set()
            for tag in text.tags:
                if tag.tag == "date":
                    dates.add(text.tokens[tag.start])
                elif tag.tag == "place":
                    place = " ".join(text.tokens[tag.start:tag.end]).lower()
                    for check_place in self.place_mappings:
                        if check_place in place:
                            countries.add(self.place_mappings[check_place])
                    
            if dates:
                tag_dict["Publication Date"] = min(dates)
            if countries:
                tag_dict["Publication Country"] = list(countries)
                    

        return text,tag_dict
    

def do_analysis(text,options,tag_dict):
    text.tags.sort()
    tag_path = []
    span_start = 0
    end_indicies = {}
    tag_loc = 0
    token_count = 0

    if "fiction" in tag_dict["Genre"]:
        genre = "prose"
    else:
        genre = tag_dict["Genre"]

    tag_dict["analysis_results"] = {}
    for tag_type in options["tags_for_analysis"]:
        tag_dict["analysis_results"][tag_type] = []

    include_tags = True
    for i in range(len(text.tokens) + 1):
        if i in end_indicies:
            if include_tags:
                token_count += i - span_start
                span_start = i
            for tag in end_indicies[i]:
                include_tags = remove_from_tag_path(tag_path,options,genre)
            del end_indicies[i]
                
        while tag_loc < len(text.tags) and i == text.tags[tag_loc].start:
            tag = text.tags[tag_loc]
            if include_tags:
                token_count += i - span_start
                span_start = i           
            if tag.end not in end_indicies:
                end_indicies[tag.end] = []
            end_indicies[tag.end].append(tag)
            include_tags = add_to_tag_path(tag,tag_path,options,genre)
            if include_tags:
                if tag.get_single_tag() in options["tags_for_analysis"]:
                    if tag.attributes and "value" in tag.attributes:
                        tag_dict["analysis_results"][tag.get_single_tag()].append(tag.attributes["value"])
                    else:
                        tag_dict["analysis_results"][tag.get_single_tag()].append(1)                    
                    
            tag_loc += 1
    tag_dict["token_count"] = token_count
        

# the function for one of the worker threads which deals with processing of individual texts
def guten_process(options,sendQ,returnQ,output_lock,fout):
    tagger = GutenTextTagger(options)
    while True:
        tag_dict = sendQ.get()
        text, tag_dict = tagger.process_text(tag_dict)
        options["not_wanted_tags"] = set(options["subcorpus" + str(tag_dict["subcorpus"]) + "_restrictions"]["not_wanted_tags"])
        options["wanted_tags"] = set(options["subcorpus" + str(tag_dict["subcorpus"]) + "_restrictions"]["wanted_tags"])
        if text:
            
            if options["mode"] == "export":
                if online:
                    fout = StringIO.StringIO()
                else:
                    if options["output_mode"] == "multiple":
                        try:
                            filename = re.sub("[^\w]","",tag_dict["Title"][0] + "by" + tag_dict["Author"][0])
                        except:
                            filename = re.sub("[^\w]","",tag_dict["Title"][0])
                        if options["num_subcorpora"] > 1:
                            filename = "sub" + str(tag_dict["subcorpus"]) + "_" + filename
                        filename = filename[:50] +tag_dict["Num"]
                        fout = codecs.open(options["output_dir"] + "/" + filename + ".xml","w",encoding="utf-8")
                    elif options["output_mode"] == "single":
                        output_lock.acquire()

                if options["output_format"] == "TEI":
                    if options["output_mode"] == "multiple":
                        fout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    fout.write('<TEI xmlns="http://www.tei-c.org/ns/1.0">\n')
                    output_header(fout,tag_dict)
                result = output_text(text,fout,options,tag_dict)
                if options["output_format"] == "TEI":
                    fout.write("</TEI>")
                if online:
                    tag_dict["text"] = fout.getvalue()
                elif options["output_mode"] == "single":
                    output_lock.release()
                else:
                    fout.close()
                if not result:
                    tag_dict = False
                    if not online and options["output_mode"] == "multiple":
                        os.remove(options["output_dir"] + "/" + filename + ".xml")
                    
            elif options["mode"] == "analyze":
                do_analysis(text,options,tag_dict)
                if tag_dict["token_count"] == 0:
                    tag_dict = 0

            elif options["mode"] == "get_texts":
                tag_dict["text"] = text               
                
            returnQ.put(tag_dict)
        else:
            returnQ.put(False)


# the main GutenTag class, iterates through the corpus and check if texts
# satisfy restrictions

class GutenTag:

    def __init__(self,options):
        if "corpus_dir" not in options:
            f = open("corpus_path.txt")
            options["corpus_dir"] = f.read()
            f.close()

        self.total_texts = 30000  ## this should be updated based on different corpora
        self.options = options
        if options["mode"] == "export" and options["output_mode"] == "single":
            fout = codecs.open(options["output_file"],"w",encoding="utf-8")
            if options["output_format"] == "TEI":
                fout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        else:
            fout = None
        self.metadata_reader = MetadataReader()
        self.worker_threads = []
        num_threads = cpu_count()/2 # use half the resources on the system
        self.sendQ = Queue()
        self.returnQ = Queue()
        self.output_lock = Lock()
        for i in range(num_threads):
            self.worker_threads.append(Process(target=guten_process,args=(options,self.sendQ,self.returnQ, self.output_lock,fout)))
            self.worker_threads[-1].daemon = True
            self.worker_threads[-1].start()
        if not "genre" in options["mode"]: 
            f = open("resources/GT_textinfo.dat","rb")
            self.genre_lookup = cPickle.load(f)
            self.publication_date_lookup = cPickle.load(f)
            self.publication_country_lookup = cPickle.load(f)
            f.close()
        else:
            self.genre_lookup = {}
            self.publication_date_lookup = {}
            self.publication_country_lookup = {}

        self.gender_classifier = GenderClassifier()

        self.lists = {}
        for i in range(1,options["num_subcorpora"] + 1):
            restriction_list = "subcorpus" + str(i) + "_restrictions"
            for restriction in options[restriction_list]:
                if restriction.endswith("_list"):
                    stuff = options[restriction_list][restriction].split("|")
                    options[restriction_list][restriction] = stuff[0]
                    f = open("user_lists/" + stuff[1])
                    self.lists[options[restriction_list][restriction]] = set()
                    for line in f:
                        self.lists[options[restriction_list][restriction]].add(line.strip())
                    f.close()
                

    def __del__(self):
        for worker_thread in self.worker_threads:
            worker_thread.terminate()


    def satisfy_basic_tag_restrictions(self,tags,restrictions):
                                     
        for restriction in restrictions:
                
            if restriction == "Num" or restriction == "lexical_restrictions" or restriction == "wanted_tags" or restriction == "not_wanted_tags":
                continue

            if restriction.endswith("_list"):
                restriction_type = restrictions[restriction]
                found = False
                if restriction_type in tags:
                    for item in tags[restriction_type]:
                        if item in self.lists[restriction_type]:
                            found = True
                if not found:
                    return False
            elif restriction == "Author Birth" or restriction == "Author Death" or restriction == "Publication Date":
                if not any([restrictions[restriction][0] <= entry <= restrictions[restriction][1] for entry in tags.get(restriction,[])]):
                    return False
            elif restriction == "Genre":
                if not "Genre" in tags or tags["Genre"] not in restrictions["Genre"]:
                    return False
    
            elif not any([restrictions[restriction].lower() in entry.lower() for entry in tags.get(restriction,[])]):
                return False
        return True

    def setup_tag_dict(self,html):
        num = html[:html.find(".")]
        if "Num" in self.options["subcorpus1_restrictions"] and int(num) not in self.options["subcorpus1_restrictions"]["Num"]:
            return None
        href, charset,tag_dict = self.metadata_reader.get_PG_metadata(self.options["corpus_dir"] + "/ETEXT/"+ html)           
        tag_dict["Num"] = num
        tag_dict["Author Gender"] = []
        tag_dict["href"] = href
        tag_dict["charset"] = charset
        tag_dict["user_id"] = self.options["id"]
        tag_dict["total_texts"] = self.total_texts
        for author in tag_dict["Author"]:
            tag_dict["Author Gender"].append(self.gender_classifier.classify(author.split(" ")[0]).lower())
        if "maxnum" in self.options:
            tag_dict["maxnum"] = self.options["maxnum"]
        if self.options["mode"] == "genre_training" and not tag_dict["Subject"]:
            return None
        if num in self.genre_lookup:
            tag_dict["Genre"] = self.genre_lookup[num]
        if num in self.publication_date_lookup:
            tag_dict["Publication Date"] = self.publication_date_lookup[num]
        if num in self.publication_country_lookup:
            tag_dict["Publication Country"] = self.publication_country_lookup[num]
        return tag_dict
        

    def get_all_tags(self):
        filenames = os.listdir(self.options["corpus_dir"] + "/" + "ETEXT")
        for html in filenames:
            tag_dict = self.setup_tag_dict(html)
            if tag_dict:
                yield tag_dict
                
    
    def iterate_over_texts(self):
        count = 0
        problem_count = 0
        filenames = os.listdir(self.options["corpus_dir"] + "/" + "ETEXT")
        if self.options["randomize_order"]:
            random.shuffle(filenames)
        i = 0
        active = 0
        not_done = True
        while  i < len(filenames) and ("maxnum" not in self.options or count < self.options["maxnum"]):
            while  i < len(filenames) and active < len(self.worker_threads) and ("maxnum" not in self.options  or active < self.options["maxnum"] - count):
                html = filenames[i]
                print html
                tag_dict = self.setup_tag_dict(html)
                if not tag_dict:
                    continue
                tag_dict["progress"] = i      
                for j in range(1, self.options["num_subcorpora"] + 1):
                    if tag_dict["href"] and self.satisfy_basic_tag_restrictions(tag_dict,self.options["subcorpus" + str(j)+ "_restrictions"]):
                        tag_dict = copy.copy(tag_dict)
                        tag_dict["subcorpus"] = j
                        self.sendQ.put(tag_dict)
                        active += 1
                        if self.options["mode"] == "get_texts":
                            break #so we don't get same text twice

                i+=1
                if i %1000 == 0 and self.options["mode"] != "get_texts":
                    tag_dict["notactive"] = True
                    yield tag_dict

            if active == len(self.worker_threads):             
                tag_dict = self.returnQ.get()
                active -= 1
                if tag_dict:
                    count += 1
                    yield tag_dict

        if i == len(filenames):
            while active > 0 and ("maxnum" not in self.options or count < self.options["maxnum"]):
                tag_dict = self.returnQ.get()
                active -= 1
                if tag_dict:
                    count += 1
                    yield tag_dict
                    
        print "SUCCESSFUL COUNT"
        print count 

      

# the main thread
def main_guten_process(main_Q,result_Q):
    while True:
        options = main_Q.get()
        if options == -1:
            break
        gr = GutenTag(options)
        for tags in gr.iterate_over_texts():
            if tags:
                result_Q.put(tags)

        result_Q.put({"user_id":options["id"],"done":True})


    


# this class handles the communication between the internal GutenTag functions
# and the external web interface
class GutentagRequestHandler(SocketServer.BaseRequestHandler):
   
    def handle(self):
        self.data = self.request.recv(4096).strip()
        if self.data.startswith("id:"):
            ID = self.data.split(":")[1]
            while not result_Q.empty():
                result = result_Q.get()
                results_dict[result["user_id"]].append(result)
            self.request.sendall(json.dumps(results_dict[ID]))
            results_dict[ID] = []
                
        else:
            options = json.loads(self.data)
            options["output_mode"] = "multiple"
            options["tagger"] = "simple"
            if online:
                if not "maxnum" in options:
                    options["maxnum"] = 10
                else:
                    options["maxnum"] = min(options["maxnum"],10)
            
            if not online and options["mode"] == "export" and not os.path.exists(options["output_dir"]):
                os.mkdir(options["output_dir"])
            main_Q.put(options)


# add elements to the webpage which require checking the user's hd
def insert_dynamic(text):
    try:
        saved_params = os.listdir("saved_parameters")
        if saved_params:
            new_options = "\n".join(["<option>" + filename + "</option>" for filename in saved_params])
            text = text.replace("<!-- saved parameters -->",  new_options)
    except:
        pass

    try:
        user_lexicons = os.listdir("user_lexicons")
        if user_lexicons:
            new_options = "\n".join(["<option>" + filename + "</option>" for filename in user_lexicons])
            text = text.replace("<!-- user lexicons -->", new_options)
    except:
        pass


    if True:
        user_lists = os.listdir("user_lists")
        if user_lists:
            new_options = "\n".join(["<option>" + filename + "</option>" for filename in user_lists])
            text = text.replace("<!-- user lists -->", new_options)

    return text
    
class GutentagWebserver(BaseHTTPRequestHandler):


    def do_GET(self):
        if self.path.strip()== "/":
            if not os.path.exists("corpus_path.txt"): # set corpus path
                self.send_response(200)
                self.send_header('Content-type',	'text/html; charset=utf-8')
                self.end_headers()
                f = open("set_corpus_path.html")
                self.wfile.write(f.read())
                f.close()
                return

            else: # load main front page
                f = open("gutentag.html")
                self.send_response(200)
                self.send_header('Content-type',	'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(insert_dynamic(f.read()).encode("utf-8"))
                f.close()
                return
        else:
            self.send_response(200)
            if ".cgi" in self.path:
                self.send_header('Content-type',	'text/html; charset=utf-8')
                self.end_headers()
                cgi_dict = {}
                for pair in [item.split("=") for item in self.path.split("?")[-1].split("&")]:
                    cgi_dict[pair[0]] = unquote(pair[1]).decode("utf-8").replace("+"," ")
                
                if "results_page.cgi" in self.path: # load results page
                    options = json.loads(cgi_dict["data"])
                    if not online and "save_filename" in options and options["save_filename"]:
                        try:
                            fout = open("saved_parameters/" + options["save_filename"],"w")
                            fout.write(cgi_dict["data"])
                            fout.close()
                        except:
                            print "there was a problem saving the parameters"

                    if config_mode:
                        self.wfile.write("Parameter file created")
                    else:     
                        num_subcorpora = options["num_subcorpora"]
                        page_id = options["id"]
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect(("localhost", port))
                        sock.send(cgi_dict["data"])
                        sock.close()

                        f = open("output.html")
                        text = f.read()
                        f.close()

                        text = text.split("INSERTHERE")

                        self.wfile.write(text[0])

                        self.wfile.write('<div class="hidden" id="user_id" data="%s"> </div>' % page_id)

                        for i in range(1, num_subcorpora + 1):

                            self.wfile.write('<div class="connector small"></div><div class="activesubcorpus"> <div class="corpusheader"><span class="corpusheader">Subcorpus %d (<span id="resultcount%d">0</span>)</span></div> <div class="subdefine"> <div class="defineframe"> <div class="outputlist" id="subdefine%d">' % (i,i,i))
                            self.wfile.write('</div></div></div><div class="corpusfooter"></div></div>')

                        self.wfile.write(text[1])


                elif "get_results.cgi" in self.path: # update results page
                    ID = cgi_dict["id"]            
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("localhost", port))
                    sock.send("id:" + ID)
                    response = sock.recv(4096)
                    total = [response]
                    while response:
                            response = sock.recv(4096)
                            total.append(response)
                    sock.close()
                    response = "".join(total)
                    self.wfile.write(response)

                elif "load_parameters.cgi" in self.path:
                    filename = cgi_dict["filename"]
                    f = open("saved_parameters/" + filename)
                    data = f.read()
                    f.close()
                    self.wfile.write(data)

                elif "check_corpus_path.cgi" in self.path:
                    path = cgi_dict["path"]
                    if os.path.exists(path + "/ETEXT"):
                        self.wfile.write("Ok, click reload on your browser")
                        fout = open("corpus_path.txt","w")
                        fout.write(path)
                        fout.close()
                    else:
                        self.wfile.write("There's a problem with the path")

            else:
                if self.path.endswith(".js"):
                    f = open(self.path[1:])
                    self.send_header('Content-type',	'application/javascript')
                elif self.path.endswith(".css"):
                    f = open(self.path[1:])
                    self.send_header('Content-type',	'text/css')
                elif self.path.endswith(".gif"):
                    f = open(self.path[1:],"rb")
                    self.send_header('Content-type',	'image/gif')
                elif self.path.endswith(".png"):
                    f = open(self.path[1:],"rb")
                    self.send_header('Content-type',	'image/png')
                elif self.path.endswith(".ico"):
                    f = open(self.path[1:],"rb")
                    self.send_header('Content-type',	'image/x-icon')
            
                self.end_headers()
                self.wfile.write(f.read())
                f.close()

def start_webserver():
    server = HTTPServer(('localhost', 8000),  GutentagWebserver)
    server.serve_forever()


def start_socketserver():
    if standalone:
        global port
    server = SocketServer.TCPServer(('localhost', 0),  GutentagRequestHandler)
    ip, port = server.server_address
    if not standalone:
        fout = open("temp_port.txt","w")
        fout.write(str(port))
        fout.close()
    server.serve_forever()

### this API is for people who want to access Gutentag directly in python

class GT_API:

    def __init__(self, corpus_path,options_path):
        f = open(options_path)
        self.options = json.loads(f.read())
        f.close()
        self.options["corpus_dir"] = corpus_path
        self.options["mode"] = "get_texts"
        self.gt = GutenTag(self.options)

    def cycle_through_texts(self):
        for info in self.gt.iterate_over_texts():
            text = info["text"]
            del info["text"]
            yield text, info

    def cycle_through_all_info(self):
        for info in self.gt.get_all_tags():
            yield info
    
    def get_text_TEI_string(self,text,text_info):
        temp = StringIO()
        output_text(text,temp,self.options,text_info)
        return temp.get_value()

###
    
        
if __name__ == "__main__":
    freeze_support()
    port = 0
    main_Q = Queue()
    result_Q = Queue()
    results_dict = defaultdict(list)
    socketthread = Thread(target=start_socketserver)
    socketthread.daemon = True
    socketthread.start()
    if not online:
        webthread = Thread(target=start_webserver)
        webthread.daemon = True
        webthread.start()
    mainprocess = Process(target=main_guten_process,args=(main_Q,result_Q))
    mainprocess.start()
    time.sleep(1)
    webbrowser.open("http://localhost:8000/",new=1)
    print "GutenTag is running"
    print "If a new browser window did not open, open a browser and go to the URL localhost:8000"
    print "Press Enter key to quit (browser window will not close, but it will no longer accept requests"
    raw_input()
    main_Q.put(-1)
    mainprocess.join()
    print "Exited"
