" Vim syntax file
" Language:	Snakemake (extended from python.vim)
" Maintainer:	Jay Hesselberth (jay.hesselberth@gmail.com)
" Last Change:	2019 Jul 26
"
" Usage
"
" copy to $HOME/.vim/syntax directory and add:
"
" au BufNewFile,BufRead Snakefile set syntax=snakemake
" au BufNewFile,BufRead *.snake set syntax=snakemake
"
" to your $HOME/.vimrc file
"
" force coloring in a vim session with:
"
" :set syntax=snakemake
"

" load settings from system python.vim (7.4)
source $VIMRUNTIME/syntax/python.vim

"
" Snakemake rules, as of version 3.3
"
" XXX N.B. several of the new defs are missing from this table i.e.
" subworkflow, touch etc
"
" rule        = "rule" (identifier | "") ":" ruleparams
" include     = "include:" stringliteral
" workdir     = "workdir:" stringliteral
" ni          = NEWLINE INDENT
" ruleparams  = [ni input] [ni output] [ni params] [ni message] [ni threads] [ni (run | shell)] NEWLINE snakemake
" input       = "input" ":" parameter_list
" output      = "output" ":" parameter_list
" params      = "params" ":" parameter_list
" message     = "message" ":" stringliteral
" threads     = "threads" ":" integer
" resources   = "resources" ":" parameter_list
" version     = "version" ":" statement
" run         = "run" ":" ni statement
" shell       = "shell" ":" stringliteral
" singularity = "singularity" ":" stringliteral
" conda       = "conda" ":" stringliteral
" shadow      = "shadow" ":" stringliteral
" group      = "group" ":" stringliteral


syn keyword pythonStatement	include workdir onsuccess onerror
syn keyword pythonStatement	ruleorder localrules configfile group
syn keyword pythonStatement	touch protected temp wrapper conda shadow
syn keyword pythonStatement	input output params message threads resources singularity wildcard_constraints
syn keyword pythonStatement	version run shell benchmark snakefile log script
syn keyword pythonStatement	rule subworkflow nextgroup=pythonFunction skipwhite

" similar to special def and class treatment from python.vim, except
" parenthetical part of def and class
syn match   pythonFunction
      \ "\%(\%(rule\s\|subworkflow\s\)\s*\)\@<=\h\w*" contained

syn sync match pythonSync grouphere NONE "^\s*\%(rule\|subworkflow\)\s\+\h\w*\s*"

let b:current_syntax = "snakemake"

" vim:set sw=2 sts=2 ts=8 noet:

