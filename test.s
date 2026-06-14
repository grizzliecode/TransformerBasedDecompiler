	.file	"test.c"
	.intel_syntax noprefix
	.text
	.section .rdata,"dr"
	.align 8
.LC0:
	.ascii "=== Decompiler Test Binary ===\0"
	.text
	.globl	print_welcome
	.def	print_welcome;	.scl	2;	.type	32;	.endef
print_welcome:
	push	rbp
	mov	rbp, rsp
	sub	rsp, 32
	lea	rax, .LC0[rip]
	mov	rcx, rax
	call	puts
	nop
	leave
	ret
	.globl	square
	.def	square;	.scl	2;	.type	32;	.endef
square:
	push	rbp
	mov	rbp, rsp
	mov	DWORD PTR 16[rbp], ecx
	mov	eax, DWORD PTR 16[rbp]
	imul	eax, eax
	pop	rbp
	ret
	.section .rdata,"dr"
.LC1:
	.ascii "The square of %d is: %d\12\0"
	.text
	.globl	main
	.def	main;	.scl	2;	.type	32;	.endef
main:
	push	rbp
	mov	rbp, rsp
	sub	rsp, 48
	call	__main
	mov	DWORD PTR -4[rbp], 5
	call	print_welcome
	mov	eax, DWORD PTR -4[rbp]
	mov	ecx, eax
	call	square
	mov	DWORD PTR -8[rbp], eax
	mov	edx, DWORD PTR -8[rbp]
	mov	eax, DWORD PTR -4[rbp]
	lea	rcx, .LC1[rip]
	mov	r8d, edx
	mov	edx, eax
	call	__mingw_printf
	mov	eax, 0
	leave
	ret
	.def	__main;	.scl	2;	.type	32;	.endef
	.ident	"GCC: (Rev13, Built by MSYS2 project) 15.2.0"
	.def	puts;	.scl	2;	.type	32;	.endef
