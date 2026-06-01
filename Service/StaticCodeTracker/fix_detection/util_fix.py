
import re
import javalang
import jsonlines
import tempfile
import os
import subprocess as sp
from javalang import tree, parse
import pandas as pd
import json


def print_line_info(line):
    print('--------------')
    # print(line['pa_source_code'][string_start:string_end])
    print(line['project'])
    print(line['file'])
    print(line['source_path'])
    print(line['bug'])
    print(line['start'])
    print(line['end'])
    print(line['ground_truth'])

def position_to_line_numbers(file_content, start, end):
    before = file_content[:start]
    after = file_content[:end]
    return len(before.split('\n')), len(after.split('\n'))

def check_entire_deletion_class(line,node,node_string):
     ## maybe is deleted entirely

    w_start = line['start']
    w_end = line['end']
    pa_java_code = line['pa_source_code']
    ch_java_code = line['ch_source_code']
    gumtree_output = line['gumtree_diff']
    pa_node_start = -1
    pa_node_end = -1
    ch_node_start = -1
    ch_node_end = -1
    modification_type = ""
    if gumtree_output!= "":
        
        for row_actions in gumtree_output['actions']:
            # if node_string in row_actions['tree'] and 'delete-tree' == row_actions['action'] :
            if node_string in row_actions['tree'] and ('delete-tree' == row_actions['action'] or 'delete-node' == row_actions['action']) :
                ## has modification 
                pattern = r'\[(\d+),(\d+)\]'
                pa_match = re.search(pattern, row_actions['tree'])
                string_start = int(pa_match.group(1))
                string_end = int(pa_match.group(2))
                pa_node_start, pa_node_end = position_to_line_numbers(pa_java_code, string_start, string_end)
                if w_start >= pa_node_start and w_end<= pa_node_end:
                    ### purely deletion
                    modification_type = 'entire_deletion'
                    save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}

                    return modification_type
    return modification_type

def list_matches_lines(line,start,end):
    output_data = []
    for row_match in line['gumtree_diff']['matches']:
        # print(row_match)
        row_match = add_lines_matches(row_match, line)
        if row_match['pa_start'] >= start and row_match['pa_end'] <= end:
            output_data.append(row_match)

    return output_data
def list_actions_lines(line,start,end):
    output_data = []
    for row_action in line['gumtree_diff']['actions']:
        row_action = add_lines_actions(row_action, line)
        if row_action['pa_start'] >= start and row_action['pa_end'] <= end:
            output_data.append(row_action)

    return output_data
def list_add_actions_lines(line,ch_node_start,ch_node_end):
    if ch_node_start == -1:
        return []
    output_data = []
    for row_action in line['gumtree_diff']['actions']:
        row_action = add_lines_actions(row_action, line)
        if row_action['ch_start'] >= ch_node_start and row_action['ch_end'] <= ch_node_end:
            output_data.append(row_action)
    return output_data


def check_entire_deletion(line,node,node_string,pa_node_start,pa_node_end):
     ## maybe is deleted entirely
    range_actions = list_actions_lines(line,pa_node_start,pa_node_end)
    w_start = line['start']
    w_end = line['end']
    gumtree_output = line['gumtree_diff']

    modification_type = ""
    if gumtree_output!= "":
        
        for row_actions in range_actions:
            if node_string in row_actions['tree'] and 'delete-tree' == row_actions['action'] :
            # if node_string in row_actions['tree'] and ('delete-tree' == row_actions['action'] or 'delete-node' == row_actions['action']) :
                ## has modification 
                
                if w_start >= row_actions['pa_start'] and w_end<= row_actions['pa_end']:
                    ### purely deletion
                    modification_type = 'entire_deletion'
                    save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}

                    # return modification_type
            if node_string in row_actions['tree'] and 'delete-node' == row_actions['action'] :
                if w_start >= row_actions['pa_start'] and w_end<= row_actions['pa_end']:
                    ### purely deletion
                    modification_type = 'node_deletion'
                    save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}

                    # return modification_type
            # if pa_node_start == row_actions['pa_start'] and 'move-tree' == row_actions['action']:
            #     modification_type = ""
            #     break
            
    return modification_type

def add_lines_actions(row_matches, line):
    pa_java_code = line['pa_source_code']
    ch_java_code = line['ch_source_code']

    pa_node_start = -1
    pa_node_end = -1
    ch_node_start = -1
    ch_node_end = -1
        
    try:    
        pattern = r'\[(\d+),(\d+)\]'
        pa_match = re.search(pattern, row_matches['tree'])
        # ch_match = re.search(pattern, row_matches['dest'])

        string_start = int(pa_match.group(1))
        string_end = int(pa_match.group(2))

        if 'insert' in row_matches['action']:
            ch_node_start, ch_node_end = position_to_line_numbers(ch_java_code, string_start, string_end)
        else:
            pa_node_start, pa_node_end = position_to_line_numbers(pa_java_code, string_start, string_end)
            
        # string_start = int(ch_match.group(1))
        # string_end = int(ch_match.group(2))
        # ch_node_start, ch_node_end = position_to_line_numbers(ch_java_code, string_start, string_end)

        row_matches['pa_start'] = pa_node_start 
        row_matches['pa_end'] = pa_node_end 
        row_matches['ch_start'] = ch_node_start 
        row_matches['ch_end'] = ch_node_end 
    except:
        row_matches['pa_start'] = -1
        row_matches['pa_end'] = -1 
        row_matches['ch_start'] = -1 
        row_matches['ch_end'] = -1
    return row_matches

def add_lines_matches(row_matches, line):
    pa_java_code = line['pa_source_code']
    ch_java_code = line['ch_source_code']

    pa_node_start = -1
    pa_node_end = -1
    ch_node_start = -1
    ch_node_end = -1
        
    try:
        pattern = r'\[(\d+),(\d+)\]'
        pa_match = re.search(pattern, row_matches['src'])
        ch_match = re.search(pattern, row_matches['dest'])

        string_start = int(pa_match.group(1))
        string_end = int(pa_match.group(2))
        pa_node_start, pa_node_end = position_to_line_numbers(pa_java_code, string_start, string_end)
            
        string_start = int(ch_match.group(1))
        string_end = int(ch_match.group(2))
        ch_node_start, ch_node_end = position_to_line_numbers(ch_java_code, string_start, string_end)

        row_matches['pa_start'] = pa_node_start 
        row_matches['pa_end'] = pa_node_end 
        row_matches['ch_start'] = ch_node_start 
        row_matches['ch_end'] = ch_node_end 
    except:
        row_matches['pa_start'] = -1
        row_matches['pa_end'] = -1 
        row_matches['ch_start'] = -1 
        row_matches['ch_end'] = -1 
    return row_matches
def is_change_anony_to_lambda(line,pa_node_start,pa_node_end,ch_node_start,ch_node_end): 
    range_actions = list_actions_lines(line,pa_node_start,pa_node_end)
    # add_range_actions = list_add_actions_lines(line,ch_node_start,ch_node_end)

    contain_anony_del = False
    contain_lambda_add = False

    for row_action in range_actions:
        if row_action['action'] == 'delete-node' and 'AnonymousClassDeclaration' in row_action['tree'] and row_action['pa_start'] == line['start']:
            contain_anony_del = True
            break

    
    for row_add_action in line['gumtree_diff']['actions']:
        if (row_add_action['action'] == 'insert-node' or  row_add_action['action'] == 'insert-tree') and 'LambdaExpression' in row_add_action['tree']:
            
            contain_lambda_add = True
            
            break
        
    if contain_anony_del and contain_lambda_add:
        return True
    else:
        return False 


def check_no_modification_with_range(line,node,node_string):
    ### purely use guntree diff
        ## 1. check gumtree results
    ### 1.1 find matches 
    ###2.2 find actiosn

    w_start = line['start']
    w_end = line['end']
    pa_java_code = line['pa_source_code']
    ch_java_code = line['ch_source_code']
    gumtree_output = line['gumtree_diff']
    no_modification_flag = True
    find_warning_in_node_flag = False
    pa_node_start = -1
    pa_node_end = -1
    ch_node_start = -1
    ch_node_end = -1

    modification_type = ""
    in_node_actions = []

    if gumtree_output!= "":
        
        for row_matches in gumtree_output['matches']:
            pa_node_start = -1
            pa_node_end = -1
            ch_node_start = -1
            ch_node_end = -1
            if node_string in row_matches['src'] and node_string in row_matches['dest']:
                pattern = r'\[(\d+),(\d+)\]'
                pa_match = re.search(pattern, row_matches['src'])
                ch_match = re.search(pattern, row_matches['dest'])

                if pa_match:
                    string_start = int(pa_match.group(1))
                    string_end = int(pa_match.group(2))
                    node_start, node_end = position_to_line_numbers(pa_java_code, string_start, string_end)
                    
                    
                    ### 1.1  find the warning is in the node
                    
                    if w_start >= node_start and w_end<= node_end:
                        pa_node_start = node_start
                        pa_node_end = node_end
                        string_start = int(ch_match.group(1))
                        string_end = int(ch_match.group(2))
                        ch_node_start, ch_node_end = position_to_line_numbers(ch_java_code, string_start, string_end)
                        find_warning_in_node_flag = True
                        break
                    
        if find_warning_in_node_flag:
            ### check the modification
            for row_actions in gumtree_output['actions']:
                if 'insert' in row_actions['action']:
                    mod_match = re.search(pattern, row_actions['tree'])
                    # print(row_actions['tree'])
                    if mod_match:
                        string_start = int(mod_match.group(1))
                        string_end = int(mod_match.group(2))
                        ch_mod_start, ch_mod_end = position_to_line_numbers(ch_java_code, string_start, string_end)
                        
                        if ch_mod_start>= ch_node_start and ch_mod_end<= ch_node_end:
                            save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':ch_mod_start,'end':ch_mod_end}
                            in_node_actions.append(save_action)
                    else:
                        continue
                        
                else:
                    mod_match = re.search(pattern, row_actions['tree'])
                    string_start = int(mod_match.group(1))
                    string_end = int(mod_match.group(2))
                    pa_mod_start, pa_mod_end = position_to_line_numbers(pa_java_code, string_start, string_end)

                    ## a change is cover the node
                    if pa_mod_start>= pa_node_start and pa_mod_end<= pa_node_end:
                        save_action ={'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_mod_start,'end':pa_mod_end}
                        in_node_actions.append(save_action)
                            
            
            ## decide whitch modification
            if len(in_node_actions) == 0:
                
                pass
            else:
                no_modification_flag  = False

                modification_flag = False 
                for row_actions in in_node_actions:
                    if 'update' in row_actions['action'] or 'move' in row_actions['action'] or 'insert' in row_actions['action']:
                        modification_flag = True

                        # if 'move' in row_actions['action']:
                        #     print_line_info(line)
                        #     print(row_actions)
                    else:
                        pass
                if modification_flag:
                    # with modification
                    modification_type = 'modification'
                    # save_action ={'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_mod_start,'end':pa_mod_end}
                    return no_modification_flag, find_warning_in_node_flag , modification_type, in_node_actions,pa_node_start, pa_node_end,ch_node_start, ch_node_end
                else:
                    ## purely deletion
                    modification_type = 'deletion'
                    # save_action ={'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_mod_start,'end':pa_mod_end}
                    return no_modification_flag, find_warning_in_node_flag , modification_type, in_node_actions,pa_node_start, pa_node_end,ch_node_start, ch_node_end

        else:

            ### not in matches maybe in the actions
            for row_actions in gumtree_output['actions']:
                if node_string in row_actions['tree'] and 'delete' in row_actions['action']:
                    ## has modification 
                    pattern = r'\[(\d+),(\d+)\]'
                    pa_match = re.search(pattern, row_actions['tree'])
                    string_start = int(pa_match.group(1))
                    string_end = int(pa_match.group(2))
                    pa_node_start, pa_node_end = position_to_line_numbers(pa_java_code, string_start, string_end)
                    if w_start >= pa_node_start and w_end<= pa_node_end:
                        find_warning_in_node_flag = True
                        break
            if find_warning_in_node_flag:
                ## find the node in actions
                ## three situation:
                ## 1. all deletion
                ## 2. has modification
                ## 3. entire deletion
                ### purely deletion

                if node_string == 'FieldDeclaration':
                    if 'delete-tree' == row_actions['action']:
                        modification_type = 'entire_deletion'
                        find_warning_in_node_flag = True
                        no_modification_flag = False 

                    


                        save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}
                    else:
                        modification_type = 'deletion'
                        find_warning_in_node_flag = True
                        no_modification_flag = False 
                        save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}
                        # save_action = list_actions_lines(line, pa_node_start,pa_node_end)
                    return no_modification_flag, find_warning_in_node_flag , modification_type, [save_action],pa_node_start, pa_node_end,ch_node_start, ch_node_end

                actions_in_node = list_actions_lines(line, pa_node_start,pa_node_end)
                no_modification_flag = False 

                for row_action in actions_in_node:
                    if 'delete-tree' == row_action['action'] and node_string in row_action['tree']:
                        modification_type = 'entire_deletion'
                        return no_modification_flag, find_warning_in_node_flag , modification_type, actions_in_node,pa_node_start, pa_node_end,ch_node_start, ch_node_end
                    
                    if 'update' in row_action['action'] or 'move' in row_action['action'] or 'insert' in row_action['action']:
                        modification_type = 'modification'
                        return no_modification_flag, find_warning_in_node_flag , modification_type, actions_in_node,pa_node_start, pa_node_end,ch_node_start, ch_node_end
                
                ### always deletions
                modification_type = 'deletion'
                return no_modification_flag, find_warning_in_node_flag , modification_type, actions_in_node,pa_node_start, pa_node_end,ch_node_start, ch_node_end

                # if 'delete-tree' == row_actions['action']:
                #     modification_type = 'entire_deletion'
                #     find_warning_in_node_flag = True
                #     no_modification_flag = False 

                    


                #     # save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}
                # else:
                #     modification_type = 'deletion'
                #     find_warning_in_node_flag = True
                #     no_modification_flag = False 
                #     # save_action = {'action':row_actions['action'], 'tree':row_actions['tree'],'start':pa_node_start,'end':pa_node_end}
                #     save_action = list_actions_lines(line, pa_node_start,pa_node_end)
                # return no_modification_flag, find_warning_in_node_flag , modification_type, [save_action],pa_node_start, pa_node_end
    ## if still not  return
    ## not in node
    if find_warning_in_node_flag:
        no_modification_flag = True
        return no_modification_flag, find_warning_in_node_flag , modification_type, [],pa_node_start, pa_node_end,ch_node_start, ch_node_end
    else:
        no_modification_flag = False
        return no_modification_flag, find_warning_in_node_flag , modification_type, [],pa_node_start, pa_node_end,ch_node_start, ch_node_end
    
### this code is trying to extract method and class with their text and start line and end lines from Java source code.
def extract_node_start_end(method_node,tree):
    startpos  = None
    endpos    = None
    startline = None
    endline   = None

    for path, node in tree:
        if startpos is not None and method_node not in path:
            endpos = node.position
            endline = node.position.line if node.position is not None else None
            break
        if startpos is None and node == method_node:
            startpos = node.position
            startline = node.position.line if node.position is not None else None
    return startpos, endpos, startline, endline

def get_node_text(startpos, endpos, startline, endline, last_endline_index,data):
    if startpos is None:
        return "", None, None, None
    else:
        startline_index = startline - 1 
        endline_index = endline - 1 if endpos is not None else None 

        # 1. check for and fetch annotations
        if last_endline_index is not None:
            for line in data[(last_endline_index + 1):(startline_index)]:
                if "@" in line: 
                    startline_index = startline_index - 1
        meth_text = "<ST>".join(data[startline_index:endline_index])
        meth_text = meth_text[:meth_text.rfind("}") + 1] 
        # print(meth_text)
        # 2. remove trailing rbrace for last methods & any external content/comments
        # if endpos is None and 
        if not abs(meth_text.count("}") - meth_text.count("{")) == 0:
            # imbalanced braces
            brace_diff = abs(meth_text.count("}") - meth_text.count("{"))

            for _ in range(brace_diff):
                meth_text  = meth_text[:meth_text.rfind("}")]    
                meth_text  = meth_text[:meth_text.rfind("}") + 1]     

        meth_lines = meth_text.split("<ST>")  
        meth_text  = "".join(meth_lines)                   
        last_endline_index = startline_index + (len(meth_lines) - 1) 

        return meth_text, (startline_index + 1), (last_endline_index + 1), last_endline_index
    
def extract_node(java_code,node):
    tree = javalang.parse.parse(java_code)
    return_list = []
    lex = None
    codelines = java_code.splitlines()
    # for _, node in tree.filter(javalang.tree.MethodDeclaration):
    for _, node in tree.filter(node):
        startpos, endpos, startline, endline = extract_node_start_end(node,tree)
        method_text, startline, endline, lex = get_node_text(startpos, endpos, startline, endline, lex,codelines)

        method_list = [startline,endline]
        return_list.append(method_list)
    return return_list #['method',start_line, end_line]

def is_constructor(java_code, m_start, m_end):
    range_list = []
    try:
        node = javalang.tree.ConstructorDeclaration
        range_list = extract_node(java_code,node)
        for r in range_list:
            if r[0] >= m_start and r[1]<= m_end and abs(r[0] - m_start) <=20 and abs(r[1] - m_end) <=20:
            # if r[0] >= m_start and r[1]<= m_end:
                return True,range_list
        return False,range_list
    except:
        return False,range_list

def only_modifier_changed(line,pa_node_start,pa_node_end,ch_node_start,ch_node_end):
    if ch_node_start == -1:
        return False   
    range_actions = list_actions_lines(line,pa_node_start,pa_node_end)
    add_range_actions = list_add_actions_lines(line,ch_node_start,ch_node_end)

    contain_other_mod_flag = False
    contain_deletion_mod = False
    contain_insert_mod = False 
    for row_action in range_actions:
        if row_action['action'] == 'delete-node' and 'Modifier:' in row_action['tree'] and pa_node_start == line['start']:
            if 'Modifier: final' in row_action['tree']:
                continue
            contain_deletion_mod = True
        elif row_action['action'] == 'update-node':
            continue
        else:
            contain_other_mod_flag = True
    
    for row_add_action in add_range_actions:
        if  row_add_action['action'] == 'insert-node' and 'Modifier:' in row_add_action['tree'] and pa_node_start == line['start'] :
            if 'Modifier: final' in row_add_action['tree']:
                continue
            contain_insert_mod =  True
        else:
            contain_other_mod_flag = False
        
    if (contain_other_mod_flag == False and contain_deletion_mod == True) or (contain_other_mod_flag == False and contain_insert_mod == True):
        return True
    else:
        return False 



def any_node_cover(line):
    node_type = ''
    pa_start = -1
    pa_end = -1
    ch_start = -1
    ch_end = -1 
    return_list = []
    for row_match in line['gumtree_diff']['matches']:
        row_match = add_lines_matches(row_match,line)
        if line['start']>= row_match['pa_start'] and line['end']<=row_match['pa_end']:
            node_type = row_match['src']
            pa_start = row_match['pa_start']
            pa_end = row_match['pa_end']
            ch_start = row_match['ch_start']
            ch_end = row_match['ch_end']
            return_list.append([node_type,pa_start,pa_end,ch_start,ch_end])
    return return_list

def find_close_typedeclaration(line):
    cover_list = any_node_cover(line)
    pa_close_start = -1
    pa_close_end = -1
    ch_close_start = -1
    ch_close_end = -1
    for cover_row in cover_list:
        if 'TypeDeclaration' in cover_row[0]:
            if pa_close_start == -1:
                pa_close_start = cover_row[1]
                pa_close_end = cover_row[2]
                ch_close_start = cover_row[3]
                ch_close_end = cover_row[4]
            else:
                if cover_row[1] > pa_close_start:
                    pa_close_start = cover_row[1]
                    pa_close_end = cover_row[2]
                    ch_close_start = cover_row[3]
                    ch_close_end = cover_row[4]
    return pa_close_start,pa_close_end,ch_close_start,ch_close_end

def has_modifier_change(line,pa_node_start,pa_node_end,ch_node_start,ch_node_end):
    range_actions = list_actions_lines(line,pa_node_start,pa_node_end)

    contain_deletion_mod = False
    contain_insert_mod = False 
    for row_action in range_actions:
        if 'Modifier:' in row_action['tree']:
            if 'Modifier: public' in row_action['tree'] or 'Modifier: private' in row_action['tree'] or 'Modifier: protected' in row_action['tree']:
                continue
            contain_deletion_mod = True
    if ch_node_start != -1:
        add_range_actions = list_add_actions_lines(line,ch_node_start,ch_node_end)
        for row_add_action in add_range_actions:
            if 'Modifier:' in row_add_action['tree']:
                if 'Modifier: public' in row_add_action['tree'] or 'Modifier: private' in row_add_action['tree'] or 'Modifier: protected' in row_add_action['tree']:
                    continue
                contain_insert_mod = True
    if contain_deletion_mod or contain_insert_mod:
        return True
    else:
        return False
    

def has_method_modifier_change(line,pa_node_start,pa_node_end,ch_node_start,ch_node_end):
    if line['end'] - line['start'] !=0 and line['field'] == '':
        range_actions = list_actions_lines(line,pa_node_start,pa_node_end)

        contain_deletion_mod = False
        contain_insert_mod = False 
        for row_action in range_actions:
            if 'Modifier:' in row_action['tree'] and line['start'] == row_action['pa_start']:
                if 'Modifier: public' in row_action['tree'] or 'Modifier: private' in row_action['tree'] or 'Modifier: protected' in row_action['tree'] or 'Modifier: final' in row_action['tree']:
                    continue
                contain_deletion_mod = True
        if ch_node_start != -1:
            add_range_actions = list_add_actions_lines(line,ch_node_start,ch_node_end)
            for row_add_action in add_range_actions:
                if 'Modifier:' in row_add_action['tree'] and ch_node_start == row_action['pa_start']:
                    if 'Modifier: public' in row_add_action['tree'] or 'Modifier: private' in row_add_action['tree'] or 'Modifier: protected' in row_add_action['tree'] or 'Modifier: final' in row_action['tree']:
                        continue
                    contain_insert_mod = True
        if contain_deletion_mod or contain_insert_mod:
            return True
        else:
            return False
    else:
        return False 


def insert_in_mul_w(line,pa_node_start,pa_node_end,ch_node_start,ch_node_end):
    range_matches = list_matches_lines(line,line['start'],line['end'])
    add_range_actions = list_add_actions_lines(line,ch_node_start,ch_node_end)
    find_exact_node_flag = False
    for each_match in range_matches:
        if each_match['pa_start'] == line['start'] and each_match['pa_end'] == line['end']:
            ch_mul_start = each_match['ch_start']
            ch_mul_end = each_match['ch_end']
            find_exact_node_flag = True
            break
    insert_exact_node_flag = False
    if find_exact_node_flag:
        for add_row_action in add_range_actions:
            if add_row_action['ch_start'] >= ch_mul_start and add_row_action['ch_end'] <= ch_mul_end:

                insert_exact_node_flag = True
                break
    return insert_exact_node_flag
def is_variable_modification(line,range_actions,add_range_actions):
    modified_flag = False
    
    null_deletion_flag = False
    other_operation_flag = False
    for each_action in range_actions:
        if 'delete-node' == each_action['action'] and 'NullLiteral' in each_action['tree'] and each_action['pa_start'] == line['start']:
            null_deletion_flag = True
        elif each_action['pa_start'] == line['start']:
            other_operation_flag = True

    if not other_operation_flag and null_deletion_flag:
        return True
        
    
    for each_action in range_actions:
        
        if line['field'] in each_action['tree']:
            modified_flag = True
        if 'label' in each_action.keys():
            if line['field'] in each_action['label']:
                modified_flag = True
        if 'AnonymousClassDeclaration' in each_action['tree'] and each_action['pa_start'] >= line['start'] and each_action['pa_end'] <= line['end']:
            modified_flag = False
            break
        # if ('VariableDeclarationStatement' in each_action['tree'] or 'Assignment' in each_action['tree']) and 'delete' in each_action['action']  and each_action['pa_start'] == each_action['pa_end'] and each_action['pa_start'] == line['start']:
        if 'VariableDeclarationStatement' in each_action['tree'] and 'delete-tree' == each_action['action']  and each_action['pa_start'] == each_action['pa_end'] and each_action['pa_start'] == line['start']:
            modified_flag = False
            break    
    return modified_flag 

def is_one_line_deletion(line,range_actions):
    for each_action in range_actions:
        if 'delete' in each_action['action']:
            if  each_action['pa_start'] <= line['start'] and each_action['pa_end'] >= line['end']:
                return True
    return False

def list_overlap_action_one_line(line,range_actions,add_range_actions,range_matches):
    return_list = []
    for row_action in range_actions:
        if (row_action['pa_start']<= line['start'] and row_action['pa_end'] >= line['start']) or (row_action['pa_start']<= line['end'] and row_action['pa_end'] >= line['start']) or (row_action['pa_start']>= line['start'] and row_action['pa_end'] <= line['end']):
            return_list.append(row_action)
    match_flag = False
    for each_match in range_matches:
        if each_match['pa_start'] == line['start'] and each_match['pa_end'] == line['end']:
            match_flag = True
            ch_start = each_match['ch_start']
            ch_end = each_match['ch_end']
            break
    if match_flag:
        for each_action in add_range_actions:
            if each_action['ch_start'] == ch_start and  each_action['ch_end'] == ch_end:
                return_list.append(each_action)
    return return_list

def has_mod_after_line(line,range_actions,add_range_actions,range_matches):
    match_list = []
    for each_match in range_matches:
        if each_match['pa_start'] == line['start'] and each_match['pa_end'] == line['end']:
            match_list.append(each_match)
            break
    modification_flag = False
    insert_flag = False
    if len(match_list) >=1:
        for each_action in add_range_actions:
            if match_list[0]['ch_end'] < each_action['ch_start'] :
                insert_flag = True
    for each_action in range_actions:
        if each_action['pa_start'] > line['end'] and 'update-node' in each_action['action']:
            modification_flag = True
            break

    return insert_flag or modification_flag
def is_pure_deletion(line,overlap_actions):
    pure_deletion_flag = True

    for each_action in overlap_actions:    
        if 'move-tree' == each_action['action']:
            if each_action['pa_start'] == line['start']:
                pure_deletion_flag = False
                break
            else:
                continue    
        if 'delete' not in each_action['action']:
            pure_deletion_flag = False
            break

        if 'delete-tree' in each_action:
            pure_deletion_flag = True
            break
        
    return pure_deletion_flag

def in_smaller_method(line,range_actions,add_range_actions,range_matches,pa_node_start,pa_node_end):
    in_smaller_method_flag = False
    for each_match in range_matches:
        if 'MethodDeclaration' in each_match['src'] and each_match['pa_start'] > pa_node_start and each_match['pa_end'] < pa_node_end and line['start'] >= each_match['pa_start'] and  line['start'] <= each_match['pa_end']:
            in_smaller_method_flag = True
            break
    for each_action in range_actions:
        if 'MethodDeclaration' in each_action['tree'] and each_action['pa_start'] > pa_node_start and each_action['pa_end'] < pa_node_end and line['start'] >= each_action['pa_start'] and  line['start'] <= each_action['pa_end']:
            in_smaller_method_flag = True
            break
    return in_smaller_method_flag  