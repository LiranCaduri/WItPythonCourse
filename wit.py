import datetime
from distutils.dir_util import copy_tree
import filecmp
import os
import random
import shutil
import string
import sys

import matplotlib.pyplot as plt
import networkx as nx


# constants
ROOT_PATH = os.getcwd()
FILES_TO_BE_IGNORE = ['.DS_Store', '.wit']
REF_PATH = ".wit/references.txt"
STAGE_PATH = '.wit/staging_area'
IMAGES_PATH = '.wit/images'


def init():
    folders = [".wit", ".wit/images", '.wit/staging_area']
    for folder in folders:
        if not os.path.isdir(folder):
            os.mkdir(os.path.join(ROOT_PATH, folder))

    with open('.wit/activated.txt', 'w') as active_file:
        active_file.write('master')


def add():
    pathToFile = sys.argv[2]
    dest = f'.wit/staging_area/{pathToFile}'

    if '.wit' in os.listdir(ROOT_PATH):
        if os.access(pathToFile, os.R_OK):
    
            if os.path.isfile(pathToFile):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy(pathToFile, dest)
            elif os.path.isdir(pathToFile):
                try:
                    if os.path.exists(dest):
                            shutil.rmtree(dest)
                    shutil.copytree(pathToFile, dest)
                except shutil.Error as e:
                    print('Directory not copied. Error: %s' % e)
                except OSError as e:
                    print('Directory not copied. Error: %s' % e)
        else:
            raise FileNotFoundError("The path supplied isn't valid.")
    else:
        raise FileNotFoundError("'.wit' directory not exist run init command on current running directory.")


def generate_commit_id():
    letters = string.hexdigits[:-6]
    return ''.join(random.choice(letters) for _ in range(40))


def commit():
    if '.wit' in os.listdir(ROOT_PATH) and sys.argv[2]:
        commit_id = generate_commit_id()
        image_path = f".wit/images/{commit_id}"
        stage_path = '.wit/staging_area/'

        os.mkdir(image_path)

        try:
            pointers = get_pointer_dict()
        except FileNotFoundError:
            parent = None
            head = None
            pointers = None
        else:
            head = pointers['HEAD']
            parent = head

        today = datetime.datetime.today()
        
        metadata = f'parent={parent}\ndate={today.ctime()}\nmessage={sys.argv[2]}'
        meta_file = open(f"{image_path}.txt", 'w+')
        meta_file.write(metadata)
        meta_file.close()

        try:
            if os.path.exists(image_path):
                shutil.rmtree(image_path)
            shutil.copytree(stage_path, image_path)
        except OSError as e:
            print('Directory not copied. Error: %s' % e)
        
        # reference
        with open(REF_PATH, 'w+') as ref_file:
            active = get_active_branch()

            if active != None and pointers != None and pointers[active] == head:
                pointers['HEAD'] = commit_id
                pointers[active] = commit_id
                ref_file.seek(0)
                ref_file.write(get_pointers_dict_as_str(pointers))

            elif pointers != None:
                pointers['HEAD'] = commit_id
                ref_file.seek(0)
                ref_file.write(get_pointers_dict_as_str(pointers))
            else:
                # if references not exist
                text = f"HEAD={commit_id}\nmaster={commit_id}"
                ref_file.seek(0)
                ref_file.write(text)
        # TODO - stop commit if not change
    else:
        raise FileNotFoundError("'.wit' directory not exist run init command on current running directory.")


def report_recursive_old(dcmp, withLeft=True, withRight=True, withDiff=True):
    if withDiff:
        for name in dcmp.diff_files:
            if name not in FILES_TO_BE_IGNORE:
                print(f"\t{dcmp.left}/{name}")
    if withLeft:
        for name in dcmp.left_only:
            if name not in FILES_TO_BE_IGNORE:
                # in stage but content is different
                print(f"\t{dcmp.left}/{name}")
    if withRight:
        for name in dcmp.right_only:
            if name not in FILES_TO_BE_IGNORE:
                # only if not in stage at all
                print(f"\t{dcmp.right}/{name}")
    for sub_dcmp in dcmp.subdirs.values():
        report_recursive_old(sub_dcmp, withLeft, withRight, withDiff)


def print_report(report):
    for line in report:
        print(f"\t{line}\n")


def status():
    try:
        # compare image to stage
        print("\nChanges to be committed:")
        with open('.wit/references.txt', 'r') as ref_file:
            head = ref_file.readline().split("=")[1].strip('\n')
    except FileNotFoundError:
        print("\tNo file has commited.")
    else:
        dcmp = filecmp.dircmp(f'{ROOT_PATH}/.wit/images/{head}', f'{ROOT_PATH}/.wit/staging_area') 
        image_to_stage_report = list(report_recursive(dcmp))
        print_report(image_to_stage_report)

    print('\nChanges not staged for commit:')

    # compare stage to project
    dcmp = filecmp.dircmp(ROOT_PATH, f'{ROOT_PATH}/.wit/staging_area')  
    stage_to_proj_report = list(report_recursive(dcmp, withLeft=False))
    print_report(stage_to_proj_report)

    print("\nUntracked files:")
    # everything that not in stage
    dcmp = filecmp.dircmp(f'{ROOT_PATH}/.wit/staging_area', ROOT_PATH)  
    not_in_stage = list(report_recursive(dcmp, withDiff=False))
    print_report(not_in_stage)


def remove():
    root_path = os.getcwd()
    rm_path = f'{root_path}/.wit/staging_area/{sys.argv[2]}'

    if '.wit' in os.listdir(root_path) and sys.argv[2]:
        try:
            if os.path.isfile(rm_path):
                os.remove(rm_path)
            elif os.path.isdir(rm_path):
                shutil.rmtree(rm_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"'{root_path}/.wit/staging_area/{sys.argv[2]}' Could not be found.\ntry run add command on the file.\n")
    else:
        raise FileNotFoundError("'.wit' directory not exist run init command on current running directory.")


def copy_to_root_folder(root_path, cur_path, commit_id):
    for filename in os.listdir(cur_path):
        if os.path.isfile(os.path.join(cur_path, filename)):
            shutil.copy(os.path.join(cur_path, filename), os.path.join(f"{root_path}/{cur_path.replace(f'{root_path}/.wit/images/{commit_id}', '')}", filename))
        elif os.path.isdir(os.path.join(cur_path, filename)):
            copy_to_root_folder(root_path, os.path.join(cur_path, filename), commit_id)
        else:
            sys.exit("Should never reach here.")


def report_recursive(dcmp, withLeft=True, withRight=True, withDiff=True):
    if withDiff:
        for name in dcmp.diff_files:
            if name not in FILES_TO_BE_IGNORE:
                yield f"\t{dcmp.left}/{name}"
    if withLeft:
        for name in dcmp.left_only:
            if name not in FILES_TO_BE_IGNORE:
                # in stage but content is different
                yield f"\t{dcmp.left}/{name}"
    if withRight:
        for name in dcmp.right_only:
            if name not in FILES_TO_BE_IGNORE:
                # only if not in stage at all
                yield f"\t{dcmp.right}/{name}"
    for sub_dcmp in dcmp.subdirs.values():
        yield from report_recursive(sub_dcmp, withLeft, withRight, withDiff)


def get_pointer_dict():
    pointers = {}
    with open(REF_PATH,'r') as ref_file:
        content = ref_file.readlines()
        for line in content:
            pointer = line.split('=')
            pointers.update({pointer[0]: pointer[1].strip('\n')})
    return pointers


def get_pointers_dict_as_str(pointers):
    text = ''
    for key, val in pointers.items():
        text += f'{key}={val}\n'
    return text


def get_active_branch():
    try:
        with open('.wit/activated.txt', 'r') as active_file:
            content = active_file.read()
    except (FileExistsError, FileNotFoundError):
        content = None
    if content:
        return content
    return None


def remove_files_from_root(root_path, commit_path): 
    for filename in os.listdir(root_path):
        if os.path.isfile(os.path.join(root_path, filename)):

            if filename not in os.listdir(commit_path):
                os.remove(os.path.join(root_path, filename))
        elif os.path.isdir(os.path.join(root_path, filename)) and filename not in FILES_TO_BE_IGNORE:
            remove_files_from_root(os.path.join(root_path, filename), os.path.join(commit_path, filename))


def  checkout():
    commit_id = sys.argv[2]

    # get commit id and head
    if commit_id:
        
        pointers = get_pointer_dict()
        if commit_id in pointers.keys():
            commit_id = pointers[commit_id]
        head = pointers['HEAD']
        
        # paths
        commit_head_folder = f"{ROOT_PATH}/.wit/images/{head}"
        stage_path = f'{ROOT_PATH}/.wit/staging_area'
        commit_folder = f"{ROOT_PATH}/.wit/images/{commit_id}"

        # check for file in and out of stage
        dcmp_image_to_stage = filecmp.dircmp(commit_head_folder, stage_path)      
        imgToStage = list(report_recursive(dcmp_image_to_stage))
        
        dcmp_proj_to_stage = filecmp.dircmp(ROOT_PATH, stage_path)    
        projToStage = list(report_recursive(dcmp_proj_to_stage, withLeft=False))
        
        # copy
        if not imgToStage and not projToStage:
            copy_to_root_folder(root_path=ROOT_PATH, cur_path=commit_folder, commit_id=commit_id)

            # update stage
            try:
                if os.path.exists(stage_path):
                    shutil.rmtree(stage_path)
                shutil.copytree(commit_folder, stage_path)
            except OSError as e:
                print('Directory not copied. Error: %s' % e)

            # remove some files from root folder
            remove_files_from_root(root_path=ROOT_PATH, commit_path=commit_folder)
            
            # update references.txt
            with open('.wit/references.txt', 'r+') as ref_file:
                pointers['HEAD'] = commit_id
                ref_file.seek(0)
                ref_file.write(get_pointers_dict_as_str(pointers))

            # search branch
            name = sys.argv[2]
            if name not in pointers.keys():
                name = ''
            
            with open('.wit/activated.txt', 'w') as active_file:
                active_file.write(name)
        else:
            print("no success")
    else:
        raise ValueError("Checkout command needs valid commit id or master.")


def graph():
    try:
        pointers = get_pointer_dict()
    except FileNotFoundError:
        raise FileNotFoundError("No Commit Has Been Found.")
    else:
        parent = pointers['HEAD']
        nodes, edges = extend_graph(parent)
        
        graph = nx.DiGraph()
        graph.add_nodes_from(nodes)

        for key, val in pointers.items():
            if val in nodes:
                graph.add_node(key)
                graph.add_edges_from([(key, val)])

        graph.add_edges_from(edges)

        nx.draw(graph, with_labels=True, node_size=8000, font_size=10)
        plt.show()


def extend_graph(parent):
    nodes = []
    edges = []
    parents = None
    
    while parent != 'None':
        nodes.append(parent)
        with open(f"{IMAGES_PATH}/{parent}.txt") as image_file:

            new_parent = image_file.readline()[7:].strip("\n")
            if len(new_parent) > 40:
                parents = new_parent.split(',')
                new_parent = parents[0]
                
        if new_parent != 'None':
            edges.append((parent, new_parent))
        if parents != None and parents[1]: 
            edges.append((parent, parents[1]))

            result = extend_graph(parents[1])
            nodes.extend(result[0])
            edges.extend(result[1])

        parent = new_parent
        parents = None

    return [nodes, edges]


def branch():
    if '.wit' in os.listdir(ROOT_PATH) and sys.argv[2]:
        name = sys.argv[2]
        pointers = get_pointer_dict()
        
        with open(REF_PATH, 'r+') as ref_file:
            head = pointers["HEAD"]
            if head != None:
                pointers.update({name: head})
                ref_file.seek(0)
                ref_file.write(get_pointers_dict_as_str(pointers))

    else:
        raise ValueError('Usage: python <filename> branch <name>')


def merge():
    if sys.argv[2] and '.wit' in os.listdir(ROOT_PATH):
        images_path = '.wit/images'
        branch_name = sys.argv[2]
        pointers = get_pointer_dict()
        
        # Setting pointers validation to merge.
        head_parent = pointers['HEAD']
        if branch_name in pointers.keys():
            branch_parent = pointers[branch_name]
        else:
            raise ValueError("Not a valid branch name.")

        if head_parent == branch_parent:
            raise ValueError("Can't merge, same branch were given.")

        # find common directory - run on both branches until both of the parents r the same
        head_commits = []
        branch_commits = []
        while head_parent != 'None':
            if len(head_parent) > 40:
                head_parent = head_parent.split(',')[1].strip('\n')    
            head_commits.append(head_parent)
            with open(f"{images_path}/{head_parent}.txt", 'r') as head_file:
                head_parent = head_file.readline().split('=')[1].strip('\n')

        while branch_parent != 'None':
            if len(branch_parent) > 40:
                branch_parent = branch_parent.split(',')[1].strip('\n')
            branch_commits.append(branch_parent)
            with open(f"{images_path}/{branch_parent}.txt", 'r') as branch_file:
                branch_parent = branch_file.readline().split('=')[1].strip('\n')

        head_commits = list(reversed(head_commits))
        branch_commits = list(reversed(branch_commits))

        smaller = len(head_commits) if len(head_commits) <= len(branch_commits) else len(branch_commits)

        common_father = None

        for i in range(smaller):
            if head_commits[i] == branch_commits[i]:
                common_father = head_commits[i]

        branch_last = pointers[branch_name]
        head = pointers['HEAD']

        try:
            copy_tree(f"{IMAGES_PATH}/{branch_last}", STAGE_PATH)
        except OSError as e:
            print('Directory not copied. Error: %s' % e)
            raise

        commit_id = generate_commit_id()
        today = datetime.datetime.today()

        metadata = f'parent={head},{branch_last}\ndate={today.ctime()}\nmessage=merge commit {head},{branch_last}'
        meta_file = open(f"{IMAGES_PATH}/{commit_id}.txt", 'w+')
        meta_file.write(metadata)
        meta_file.close()

        try:
            copy_tree(STAGE_PATH, f"{IMAGES_PATH}/{commit_id}")
        except OSError as e:
            print('Directory not copied. Error: %s' % e)
            raise

        # forword the HEAD pointer and active directory
        with open(REF_PATH, 'w+') as ref_file:
            active = get_active_branch()

            if active != None and pointers != None and pointers[active] == head:
                pointers['HEAD'] = commit_id
                pointers[active] = commit_id
                ref_file.seek(0)
                ref_file.write(get_pointers_dict_as_str(pointers))
            else:
                raise Exception("in else fuck!")
        
    else:
        raise ValueError('Usage: python <filename> merge <branch name>')


def main():
    commands = {
        "init": init,
        "add": add,
        "commit": commit,
        "status": status,
        "rm": remove,
        "checkout": checkout,
        "graph": graph,
        "branch": branch,
        "merge": merge
    }

    if sys.argv[1] in commands.keys():
        commands[sys.argv[1]]()
    else:
        print("Command does not exist.")


if __name__ == '__main__':
    main()

# git repo
# https://github.com/LiranCaduri/WItPythonCourse

# Reupload