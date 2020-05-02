"""CPU functionality."""

import sys
from datetime import datetime  # Needed for timer interrupt

# Opcodes:

ADD = 0b10100000
CALL = 0b01010000
CMP = 0b10100111
DEC = 0b01100110
DIV = 0b10100011
HLT = 0b00000001
INC = 0b01100101
IRET = 0b00010011
JEQ = 0b01010101
JMP = 0b01010100
JNE = 0b01010110
LD = 0b10000011
LDI = 0b10000010
MUL = 0b10100010
OR = 0b10101010
POP = 0b01000110
PRA = 0b01001000
PRN = 0b01000111
PUSH = 0b01000101
RET = 0b00010001
ST = 0b10000100
SUB = 0b10100001

# Reserved General-purpose register numbers:

IM = 5
IS = 6
SP = 7

# CMP flags:

FL_LT = 0b100
FL_GT = 0b010
FL_EQ = 0b001

# IS flags

IS_TIMER = 0b00000001
IS_KEYBOARD = 0b00000010


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self.pc = 0  # Program Counter
        self.fl = 0  # Flags
        self.ie = 1  # Flag to indicate interrupts enabled

        self.halted = False

        self.last_timer_int = None

        self.inst_set_pc = False  # True if this instruction set the PC

        self.ram = [0] * 256

        self.reg = [0] * 8
        self.reg[SP] = 0xf4

        #Branch Table
        self.branchtable = {  
            ADD: self.handle_add,
            CALL: self.handle_call,
            CMP: self.handle_cmp,
            DEC: self.handle_dec,
            DIV: self.handle_div,
            HLT: self.handle_hlt,
            INC: self.handle_inc,
            IRET: self.handle_iret,
            JEQ: self.handle_jeq,
            JMP: self.handle_jmp,
            JNE: self.handle_jne,
            LD: self.handle_ld,
            LDI: self.handle_ldi,
            MUL: self.handle_mul,
            OR: self.handle_or,
            POP: self.handle_pop,
            PRA: self.handle_pra,
            PRN: self.handle_prn,
            PUSH: self.handle_push,
            RET: self.handle_ret,
            ST: self.handle_st,
            SUB: self.handle_sub,
        }

    def load(self):
        address = 0
        
        try:
            with open(sys.argv[1]) as file:
                for line in file:
                    if line[0].startswith('0') or line[0].startswith('1'):
                        num = line.split('#')[0]
                        num = num.strip()
                        self.ram[address] = int(num, 2)
                        address += 1

        except FileNotFoundError:
            print(f"{sys.argv[0]}: {sys.argv[1]} Not found")
            sys.exit()
    
    def ram_write(self, mdr, mar):
        self.ram[mar] = mdr

    def ram_read(self, mar):
        return self.ram[mar]
    
    def push_val(self, val):
      self.reg[SP] -= 1
      self.ram_write(val, self.reg[7])
    
    def phandle_val(self):
      val = self.ram_read(self.reg[7])
      self.reg[SP] += 1

      return val
        
        # Harcoded Code That I've Removed
        # # For now, we've just hardcoded a program:

        # program = [
        #     # From print8.ls8
        #     0b10000010, # LDI R0,8
        #     0b00000000,
        #     0b00001000,
        #     0b01000111, # PRN R0
        #     0b00000000,
        #     0b00000001, # HLT
        # ]

        # for instruction in program:
        #     self.ram[address] = instruction
        #     address += 1

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        elif op == "SUB":
            self.reg[reg_a] -= self.reg[reg_b]
        elif op == "MUL":
            self.reg[reg_a] *= self.reg[reg_b]
        elif op == "DIV":
            self.reg[reg_a] /= self.reg[reg_b]
        elif op == "DEC":
            self.reg[reg_a] -= 1
        elif op == "INC":
            self.reg[reg_a] += 1
        elif op == "CMP":
            self.fl &= 0x11111000  # Clear all CMP flags
            if self.reg[reg_a] < self.reg[reg_b]:
                self.fl |= FL_LT
            elif self.reg[reg_a] > self.reg[reg_b]:
                self.fl |= FL_GT
            else:
                self.fl |= FL_EQ
        elif op == "OR":
            self.reg[reg_a] |= self.reg[reg_b]
        else:
            raise Exception("Unsupported ALU operation")
    
    def check_for_timer_int(self):
      """Check the time to see if a timer interrupt should fire."""
      if self.last_timer_int == None:
        self.last_timer_int = datetime.now()
      now = datetime.now()

      diff = now - self.last_timer_int

      if diff.seconds >= 1:  
            self.last_timer_int = now
            self.reg[IS] |= IS_TIMER

    def handle_ints(self):
        if not self.ie:  # See if interrupts enabled
            return

        # Mask out interrupts
        masked_ints = self.reg[IM] & self.reg[IS]
        for i in range(8):
            # See if the interrupt triggered
            if masked_ints & (1 << i):
                self.ie = 0   # disable interrupts
                self.reg[IS] &= ~(1 << i)  # clear bit for this interrupt

                # Save all the work on the stack
                self.push_val(self.pc)
                self.push_val(self.fl)
                for r in range(7):
                    self.push_val(self.reg[r])

                # Look up the address vector and jump to it
                self.pc = self.ram_read(0xf8 + i)

                break  # no more processing

    def trace(self):
        print(f"TRACE: %02X | %02X | %d | %02X %02X %02X |" % (
            self.pc,
            self.fl,
            self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')

        for i in range(8):
            print(" %02X" % self.reg[i], end='')

        print()

    def run(self):
        """Run the CPU."""
        while not self.halted:
            # Interrupt code

            self.check_for_timer_int()     # Checking for timer interrupt 
            self.handle_ints()             # Check if any interrupts occurred


            ir = self.ram[self.pc]
            operand_a = self.ram_read(self.pc + 1)
            operand_b = self.ram_read(self.pc + 2)

            inst_size = ((ir >> 6) & 0b11) + 1
            self.inst_set_pc = ((ir >> 4) & 0b1) == 1

            if ir in self.branchtable:
                self.branchtable[ir](operand_a, operand_b)
            else:
                raise Exception(
                    f"Invalid instruction {hex(ir)} at address {hex(self.pc)}")

            # If the instruction didn't set or change the PC, just move to the next instruction
            if not self.inst_set_pc:
                self.pc += inst_size

    def handle_ldi(self, operand_a, operand_b):
        self.reg[operand_a] = operand_b

    def handle_prn(self, operand_a, operand_b):
        print(self.reg[operand_a])

    def handle_pra(self, operand_a, operand_b):
        print(chr(self.reg[operand_a]), end='')
        sys.stdout.flush()

    def handle_add(self, operand_a, operand_b):
        self.alu("ADD", operand_a, operand_b)

    def handle_sub(self, operand_a, operand_b):
        self.alu("SUB", operand_a, operand_b)

    def handle_mul(self, operand_a, operand_b):
        self.alu("MUL", operand_a, operand_b)

    def handle_div(self, operand_a, operand_b):
        self.alu("DIV", operand_a, operand_b)

    def handle_dec(self, operand_a, operand_b):
        self.alu("DEC", operand_a, None)

    def handle_inc(self, operand_a, operand_b):
        self.alu("INC", operand_a, None)

    def handle_or(self, operand_a, operand_b):
        self.alu("OR", operand_a, operand_b)

    def handle_pop(self, operand_a, operand_b):
        self.reg[operand_a] = self.phandle_val()

    def handle_push(self, operand_a, operand_b):
        self.push_val(self.reg[operand_a])

    def handle_call(self, operand_a, operand_b):
        self.push_val(self.pc + 2)
        self.pc = self.reg[operand_a]

    def handle_ret(self, operand_a, operand_b):
        self.pc = self.phandle_val()

    def handle_ld(self, operand_a, operand_b):
        self.reg[operand_a] = self.ram_read(self.reg[operand_b])

    def handle_st(self, operand_a, operand_b):
        self.ram_write(self.reg[operand_b], self.reg[operand_a])

    def handle_jmp(self, operand_a, operand_b):
        self.pc = self.reg[operand_a]

    def handle_jeq(self, operand_a, operand_b):
        if self.fl & FL_EQ:
            self.pc = self.reg[operand_a]
        else:
            self.inst_set_pc = False

    def handle_jne(self, operand_a, operand_b):
        if not self.fl & FL_EQ:
            self.pc = self.reg[operand_a]
        else:
            self.inst_set_pc = False

    def handle_cmp(self, operand_a, operand_b):
        self.alu("CMP", operand_a, operand_b)

    def handle_iret(self, operand_a, operand_b):
        # Restore work from the stack
        for i in range(6, -1, -1):
            self.reg[i] = self.phandle_val()
        self.fl = self.phandle_val()
        self.pc = self.phandle_val()

        # Enable interrupts 
        self.ie = 1

    def handle_hlt(self, operand_a, operand_b):
        self.halted = True
