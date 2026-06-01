
import re
import javalang
import jsonlines
import tempfile
import os
import subprocess as sp
from javalang import tree, parse
import pandas as pd
import json
import util_fix as util


def heuristic(file_path,outfile_path):
    count = 0 

    f = 0
    p = 0
    d = 0 
    fn=0
    fp=0
    tp =0
    tn=0


    data = []
    type_deletion = 0 
    label_deletion = 0 
    label_fix = 0

    with jsonlines.open(file_path) as reader:
        # print(len(list(reader)))

        for line in reader:
            label_deletion_flag  = False
            label_fix_flag = False 
            count += 1     
            if line['scope'] == 'class': #(1&2)
            # if line['scope'] == 'class':
                label_deletion_flag  = True
            ### 
            elif line['is_file_change'] == 'F':
                ## 3 
                label_deletion_flag = True
            else:
                
                ## check TypeDeclaration
                ## label unchanged field as deletion
                node = javalang.tree.TypeDeclaration
                type_node_string = 'TypeDeclaration'
                type_modification_type =  util.check_entire_deletion_class(line,node,type_node_string)
                
                
                node = javalang.tree.ClassDeclaration
                class_node_string = 'ClassOrInterfaceDeclaration'
                class_modification_type =  util.check_entire_deletion_class(line,node,class_node_string)
                if class_modification_type == 'entire_deletion' or type_modification_type == 'entire_deletion':
                    ##1
                    ## if the entire class is deleted
                    label_deletion_flag = True

                else:
                    class_no_modification_flag, class_find_warning_in_node_flag , class_modification_type, class_in_node_actions,class_pa_node_start, class_pa_node_end,class_ch_node_start,class_ch_node_end =  check_no_modification_with_range(line,node,class_node_string)
                    type_no_modification_flag, type_find_warning_in_node_flag , type_modification_type, type_in_node_actions,type_pa_node_start, type_pa_node_end,type_ch_node_start,type_ch_node_end =  check_no_modification_with_range(line,node,type_node_string)
                    if (class_find_warning_in_node_flag and class_no_modification_flag) or (type_find_warning_in_node_flag and type_no_modification_flag):    
                        ## 3 
                        ## if the entire class has no modification
                        label_deletion_flag = True
                    else:
                        node = javalang.tree.MethodDeclaration
                        node_string = 'MethodDeclaration'

                        method_no_modification_flag, method_find_warning_in_node_flag , method_modification_type, method_in_node_actions,method_pa_node_start, method_pa_node_end,method_ch_node_start,method_ch_node_end =  check_no_modification_with_range(line,node,node_string)
                        

                        if method_find_warning_in_node_flag:
                            method_modification_type =  util.check_entire_deletion(line,node,node_string,method_pa_node_start,method_pa_node_end)
                            if method_modification_type == 'entire_deletion' or (method_modification_type == 'node_deletion' and method_ch_node_start == -1):
                                if not util.is_change_anony_to_lambda(line,method_pa_node_start,method_pa_node_end,method_ch_node_start,method_ch_node_end):
                                    ## 2
                                    ## if the entire method has no modification
                                    label_deletion_flag = True

                            ## 41 
                            ## if the warning is in a constructor, and if it has no any modification
                            row_actions = util.list_actions_lines(line,method_pa_node_start,method_pa_node_end)
                            if label_fix_flag == False and label_deletion_flag == False:
                                constructor_flag, range_list  =  util.is_constructor(line['pa_source_code'],method_pa_node_start,method_pa_node_end)
                                if constructor_flag:
                                    ## check any modification
                                    if len(row_actions) == 0:
                                        label_deletion_flag = True
                            ### 42
                            ## if the warning is in a field, and check if its modifer changes
                            if label_fix_flag == False and label_deletion_flag == False:
                                node = javalang.tree.FieldDeclaration
                                node_string = 'FieldDeclaration'
                                # no_modification_flag,find_warning_in_node_flag = check_no_modification(line,node,node_string)
                                # no_modification_flag,find_warning_in_node_flag,del_list, add_list,w_node_start, w_node_end =  check_no_modification_with_range(line,node,node_string)
                                field_no_modification_flag, field_find_warning_in_node_flag , field_modification_type, field_in_node_actions,field_pa_node_start, field_pa_node_end,field_ch_node_start,field_ch_node_end =  check_no_modification_with_range(line,node,node_string)
                                if field_find_warning_in_node_flag:
                                
                                    if method_pa_node_start < field_pa_node_start and method_pa_node_end> field_pa_node_end:
                                        if util.only_modifier_changed(line,field_pa_node_start,field_pa_node_end,field_ch_node_start,field_ch_node_end):
                                            label_fix_flag = True
                                        else:
                                            label_deletion_flag = True
                            ### 51
                            ## if the warning is in a method, and check if the entire method has any modification
                            if label_fix_flag == False and label_deletion_flag == False:
                                if method_no_modification_flag and not constructor_flag:
                                    label_deletion_flag = True

                            ### 52
                            ## if the warning indicates the entire method, and check if the method's modifier changes
                            if label_fix_flag == False and label_deletion_flag == False:
                                if not method_no_modification_flag and not constructor_flag:
                                    if util.has_method_modifier_change(line,method_pa_node_start,method_pa_node_end,method_ch_node_start,method_ch_node_end):
                                        label_fix_flag = True

                            ### 53
                            ## if method has pure deletion modifications
                            if label_fix_flag == False and label_deletion_flag == False:
                                if not method_no_modification_flag and not constructor_flag:
                                    range_actions = util.list_actions_lines(line,method_pa_node_start,method_pa_node_end)
                                    add_range_actions = util.list_add_actions_lines(line,method_ch_node_start,method_ch_node_end)
                                    range_matches = util.list_matches_lines(line,line['start'], line['end'])
                                    pure_deletion_flag = False
                                    if len(add_range_actions) != 0:
                                        pure_deletion_flag = False
                                    else:
                                        pure_deletion_flag = True
                                        for each_action in range_actions:
                                            if 'delete' not in each_action['action']:
                                                pure_deletion_flag = False

                                        if pure_deletion_flag:
                                            label_deletion_flag = True
                                    if pure_deletion_flag == False and label_deletion_flag == False and label_fix_flag == False:
                                        
                                        if line['end'] - line['start'] != 0:
                                            if line['field'] != '':
                                                ### 541
                                                ## if the warning has field name, check if there is the field-related changes
                                                if not util.is_variable_modification(line,range_actions,add_range_actions):
                                                    label_deletion_flag = True
                                                else:
                                                    if util.in_smaller_method(line,range_actions,add_range_actions,range_matches,method_pa_node_start,method_pa_node_end):
                                                        label_deletion_flag = True
                                            else:
                                                ### 542
                                                ## if the warning has no field name, check if there is any block that contains this warning and if there are modification in the block 
                                                if not util.insert_in_mul_w(line,method_pa_node_start,method_pa_node_end,method_ch_node_start,method_ch_node_end):
                                                    label_deletion_flag = True
                                        else:
                                            ### 55
                                            ## 551
                                            ## if the warning has field name, check if there is the field-related changes, and the definition statement of the field is not deleted
                                            if line['field']!="":
                                                if util.is_one_line_deletion(line,range_actions) or not util.is_variable_modification(line,range_actions,add_range_actions):
                                                    label_deletion_flag = True
                                            else:

                                                overlap_actions  = util.list_overlap_action_one_line(line,range_actions,add_range_actions,range_matches)
                                                if len(overlap_actions) == 0:
                                                    ### 552
                                                    # if the warning has modification after the start line of the warning
                                                    if not util.has_mod_after_line(line,range_actions,add_range_actions,range_matches):
                                                        label_deletion_flag = True
                                                else:
                                                    ### 553
                                                    # if the overlapped modifications are all deletions.
                                                    if util.is_pure_deletion(line,overlap_actions):
                                                        label_deletion_flag = True
                        ### 42 
                        # ## if the warning is in a field, and check if its modifer changes                    
                        elif not method_find_warning_in_node_flag and line['start']!=-1:
                            
                            
                            node = javalang.tree.FieldDeclaration
                            node_string = 'FieldDeclaration'
                            # no_modification_flag,find_warning_in_node_flag = check_no_modification(line,node,node_string)
                            # no_modification_flag,find_warning_in_node_flag,del_list, add_list,w_node_start, w_node_end =  check_no_modification_with_range(line,node,node_string)
                            field_no_modification_flag, field_find_warning_in_node_flag , field_modification_type, field_in_node_actions,field_pa_node_start, field_pa_node_end,field_ch_node_start,field_ch_node_end =  check_no_modification_with_range(line,node,node_string)
                            
                            if field_find_warning_in_node_flag:
                                if util.only_modifier_changed(line,field_pa_node_start,field_pa_node_end,field_ch_node_start,field_ch_node_end):
                                    label_fix_flag = True
                                else:
                                    label_deletion_flag = True
                            else:

                                ### 43
                                # if the warning is out of method, field, constructor. check the class containing the warning and check if the class's modifer changes
                                if line['end'] - line['start'] == 0:
                                    label_deletion_flag = True
                                else:
                                    if len(line['gumtree_diff'])  != 0:
                                        pa_node_start,pa_node_end,ch_node_start,ch_node_end = util.find_close_typedeclaration(line)
                                        if pa_node_start== -1:
                                            label_deletion_flag = True

                                        else:
                                            modifier_change_flag = util.has_modifier_change(line,pa_node_start,pa_node_end,ch_node_start,ch_node_end)

                                            if not modifier_change_flag:
                                                label_deletion_flag = True
                        elif line['start'] == -1 and line['end'] == -1:
                            ## same(4) warnings are reported start:-1 and end:-1 label them as non-fixed  
                            label_deletion_flag = True



            if (label_fix_flag == True and label_deletion_flag == False) or (label_deletion_flag ==False and label_fix_flag == False):
                label_fix +=1
                line['label'] = 'fix'
                data.append(line)
                if line['ground_truth'] == 'fix':
                    tp +=1
                else:
                    fp+=1
            elif label_fix_flag == False and label_deletion_flag == True:   
                
                label_deletion +=1

                line['label'] = 'deletion'
                data.append(line)

                if line['ground_truth'] == 'deletion':
                    tn +=1
                else:
                    fn +=1

    print(f"count:{count}")
    print(f"fix:{f}")
    print(f"deletion:{d}")
    print(f"tp:{tp}")
    print(f"fp:{fp}")
    print(f"tn:{tn}")
    print(f"fn:{fn}")
    print(f"precision:{tp/(tp+fp)}")
    print(f"recall:{tp/(tp+fn)}")

    with jsonlines.open(outfile_path, mode='w') as writer:
        writer.write_all(data) 

if __name__ == '__main__':
    ### the file_path is the path of metadata.jsonl
    ### the output_file_path is the path of results.jsonl
    file_path = r"/home/junjie/Desktop/tracking_static/Experiment_data/Fix_detection/metadata_results_SOTA_RQ1&2/metadata.jsonl"
    outfile_path = r"/home/junjie/Desktop/tracking_static/Experiment_data/Fix_detection/metadata_results_SOTA_RQ1&2/results.jsonl"
    heuristic(file_path,outfile_path)