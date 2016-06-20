#-------------------------------------------------------------------------------
# . File      : AminoLibrary.py
# . Program   : MolarisTools
# . Copyright : USC, Mikolaj Feliks (2016)
# . License   : GNU GPL v3.0       (http://www.gnu.org/licenses/gpl-3.0.en.html)
#-------------------------------------------------------------------------------
# . Atoms are not children of a group.
# . The groups only contain serial numbers of atoms.
#
#               AminoLibrary
#                 /       \
#                /         \
#   AminoComponent     AminoComponent
#                      /      |     \
#                     /       |      \
#              AminoGroups  bonds  AminoAtoms

from    Utilities           import TokenizeLine
from    ParametersLibrary   import ParametersLibrary
import  collections, exceptions, os


AminoAtom  = collections.namedtuple ("Atom"  , "atomLabel  atomType  atomCharge")
AminoGroup = collections.namedtuple ("Group" , "natoms  centralAtom  radius  labels  symbol")

_DEFAULT_DIVIDER = "-" * 41
_GROUP_START     = "A"


class AminoComponent (object):
    """A class to represent a residue."""

    def __init__ (self, logging=True, verbose=False, **keywordArguments):
        """Constructor."""
        for (key, value) in keywordArguments.iteritems ():
            if key != "logging":
                setattr (self, key, value)
        # . Print info
        if logging: self.Info (verbose=verbose)


    def Info (self, verbose=False):
        """Print info."""
        print ("Component: %d %s (%d atoms, %d bonds, %d groups, %-5.2f charge%s)" % (self.serial, self.name, self.natoms, self.nbonds, self.ngroups, self.charge, (", %s" % self.title) if verbose else ""))


    @property
    def natoms (self):
        if hasattr (self, "atoms"):
            return len (self.atoms)
        else:
            return 0

    @property
    def nbonds (self):
        if hasattr (self, "bonds"):
            return len (self.bonds)
        else:
            return 0

    @property
    def nangles (self):
        if hasattr (self, "angles"):
            return len (self.angles)
        else:
            return 0

    @property
    def ntorsions (self):
        if hasattr (self, "torsions"):
            return len (self.torsions)
        else:
            return 0

    @property
    def ngroups (self):
        if hasattr (self, "groups"):
            return len (self.groups)
        else:
            return 0

    @property
    def charge (self):
        if hasattr (self, "atoms"):
            total = 0.
            for atom in self.atoms:
                total += atom.atomCharge
            return total
        else:
            return 0.

    @property
    def label (self):
        if hasattr (self, "name"):
            return self.name
        return ""

    @label.setter
    def label (self, new):
        if hasattr (self, "name"):
            self.name = new


    def CalculateGroup (self, group):
        """Calculate the charge of a group."""
        total = 0.
        for atom in self.atoms:
            if atom.atomLabel in group.labels:
                total += atom.atomCharge
        return total


    _DEFAULT_MODIFY = {
        "A" :   ("O3",  "O-"),
        "B" :   ("O3",  "O-"),
        "C" :   ("O3",  "O-"),
        }
    def WriteDict (self, groups=None, nstates=2, modify=_DEFAULT_MODIFY):
        """Generate Python code to use in evb_assign.py type of script."""
        # . If no symbols defined, take the whole component
        groupSymbols = groups
        if groupSymbols is None:
            groupSymbols = []
            for group in self.groups:
                groupSymbols.append (group.symbol)
        # . Start here
        print ("names = {")
        for symbol in groupSymbols:
            # . Pick a group of atoms
            found = False
            for group in self.groups:
                if group.symbol == symbol:
                    found = True
                    break
            if not found:
                raise exceptions.StandardError ("Group %s not found." % symbol)
            # . Run for each atom in the group
            for label in group.labels:
                for atom in self.atoms:
                    if atom.atomLabel == label:
                        break
                atype   = atom.atomType
                # . Check if the atom type has to be modified
                if modify.has_key (symbol):
                    oldType, newType = modify[symbol]
                    if oldType == atype:
                        atype = newType
                    else:
                        atype = "%s0" % atype[0]
                else:
                    atype = "%s0" % atype[0]

                acharge = atom.atomCharge
                line    = "%-6s  :  (" % ("\"%s\"" % atom.atomLabel)
                # . For each atom, generate entries for n states
                for i in range (nstates):
                    if i > 0:
                        line = "%s  ,  (%5.2f , \"%2s\")" % (line, acharge, atype)
                    else:
                        line = "%s(%5.2f , \"%2s\")" % (line, acharge, atype)
                print ("%s) ," % line)
            # . Separate groups
            print ("\\")
        # . Finish up
        print ("}")


    def Write (self, filename=None, title=None, showGroups=False, showLabels=False, sortGroups=False, terminate=True):
        """Write component in a format understandable by Molaris."""
        output = []
        output.append (_DEFAULT_DIVIDER)
        # . Write header
        if title is None:
            if hasattr (self, "title"):
                title = self.title
        output.append ("%3d%s%s" % (self.serial, self.name, ("  ! %s" % title) if title else ""))

        # . Prepare a list of atoms
        atoms = self.atoms
        if sortGroups:
            atoms = []
            for group in self.groups:
                for atom in self.atoms:
                    if atom.atomLabel in group.labels:
                        atoms.append (atom)

        # . Prepare conversion table label->serial
        convert = {"" : 0, }
        for atomSerial, atom in enumerate (atoms, 1):
            convert[atom.atomLabel] = atomSerial

        # . Write atoms
        output.append ("%5d  ! Number of atoms" % self.natoms)
        for atom in atoms:
            markGroup = ""
            if showGroups:
                for igroup, group in enumerate (self.groups):
                    if atom.atomLabel in group.labels:
                        markGroup   = "  %s ! %s" % ("   " if (igroup % 2 == 1) else "", group.symbol)
                        break
            output.append ("%5d %-4s %4s %6.2f%s" % (convert[atom.atomLabel], atom.atomLabel, atom.atomType, atom.atomCharge, markGroup))

        # . Reorder bonds after sorting the groups
        bonds = self.bonds
        if sortGroups:
            # . Prepare serial bonds
            serialBonds = []
            for labela, labelb in self.bonds:
                seriala, serialb = convert[labela], convert[labelb]
                # . Keep the lower serial first
                if seriala > serialb:
                    seriala, serialb = serialb, seriala
                serialBonds.append ([seriala, serialb])
            # . Sort bonds
            serialBonds.sort (key=lambda bond: (bond[0], bond[1]))
            # . Invert the conversion table label->serial to serial->label
            trevnoc = {}
            for label, serial in convert.iteritems ():
                trevnoc[serial] = label
            # . Convert serial bonds to label bonds
            bonds = []
            for seriala, serialb in serialBonds:
                labela, labelb = trevnoc[seriala], trevnoc[serialb]
                pair = labela, labelb
                bonds.append (pair)
            # . We are done!

        # . Write bonds
        output.append ("%5d  ! Number of bonds" % self.nbonds)
        for labela, labelb in bonds:
            label = ""
            if showLabels:
                label = "%4s %4s" % (labela, labelb)
            output.append ("%5d%5d%s" % (convert[labela], convert[labelb], ("    ! %s" % label) if showLabels else ""))

        # . Write connecting atoms
        labela, labelb = self.connect
        clabels = ""
        if labela != "" or labelb != "":
            clabels = " (%s, %s)" % (labela, labelb)
        output.append ("%5d%5d  ! Connecting atoms%s" % (convert[labela], convert[labelb], clabels))

        # . Write groups
        output.append ("%5d  ! Number of electroneutral groups" % self.ngroups)
        totalCharge = 0.
        for group in self.groups:
            output.append ("%5d%5d%6.1f" % (group.natoms, convert[group.centralAtom], group.radius))
            # . Sort atoms in a group depending on their serial
            serials = []
            for atomLabel in group.labels:
                serials.append (convert[atomLabel])
            serials.sort ()
            # . Write serials of the group
            line = "    "
            for serial in serials:
                line = "%s%d  " % (line, serial)
            if showGroups:
                line = "%s  ! Group %s: %.4f" % (line, group.symbol, self.CalculateGroup (group))
                totalCharge += self.CalculateGroup (group)
            output.append (line)
        # . Finish up
        output.append ("%5d%s" % (0, "  ! Total charge: %.4f" % totalCharge if showGroups else ""))
        # . Make it the last component in the library
        if terminate:
            output.append (_DEFAULT_DIVIDER)
            output.append ("%5d" % 0)
            output.append (_DEFAULT_DIVIDER)
        # . Write to a file or terminal
        if filename:
            fo = open (filename, "w")
            for line in output:
                fo.write ("%s\n" % line)
            fo.close ()
        else:
            for line in output:
                print line


    def KillAtom (self, label, correctCharges=False):
        """Delete an atom from the component."""
        # . Remove from the list of atoms
        newAtoms   = []
        for atom in self.atoms:
            if not atom.atomLabel == label:
                newAtoms.append (atom)
            else:
                charge = atom.atomCharge
        if len (newAtoms) == len (self.atoms):
            raise exceptions.StandardError ("Atom %s not found." % label)
        self.atoms = newAtoms
        # . Add the charge of the killed atom to other charges in the same group
        if correctCharges:
            pass
        # . Remove bonds that include the killed atom
        newBonds   = []
        for labela, labelb in self.bonds:
            if not (labela == label or labelb == label):
                pair = (labela, labelb)
                newBonds.append (pair)
        self.bonds = newBonds
        # . Modify the group that includes the killed atom
        newGroups  = []
        for group in self.groups:
            labels     = []
            foundGroup = False
            for atomLabel in group.labels:
                if atomLabel == label:
                    foundGroup = True
                else:
                    labels.append (atomLabel)
            if foundGroup:
                if label == group.centralAtom:
                    centralAtom = labels[len (labels) / 2]
                else:
                    centralAtom = group.centralAtom
                newGroup = AminoGroup (natoms=(group.natoms - 1), centralAtom=centralAtom, radius=group.radius, labels=labels, symbol=group.symbol)
            else:
                newGroup = group
            newGroups.append (newGroup)
        self.groups = newGroups


    def KillBond (self, label, labelOther):
        """Delete a bond from the component."""
        pass


    def ReplaceAtom (self, label, newLabel, newType, newCharge):
        """Replace the label, type and charge of an atom."""
        # . Replace in the list of atoms
        found    = False
        newAtoms = []
        for atom in self.atoms:
            if atom.atomLabel == label:
                found = True
                atom  = AminoAtom (atomLabel=newLabel, atomType=newType, atomCharge=newCharge)
            newAtoms.append (atom)
        if not found:
            raise exceptions.StandardError ("Atom %s not found." % label)
        self.atoms = newAtoms

        # . Replace in the list of bonds
        newBonds = []
        for bonda, bondb in self.bonds:
            if   bonda == label:
                bonda = newLabel
            elif bondb == label:
                bondb = newLabel
            newBonds.append ((bonda, bondb))
        self.bonds = newBonds

        # . Replace in the group
        newGroups = []
        for group in self.groups:
            found     = False
            newLabels = []
            for atomLabel in group.labels:
                if atomLabel == label:
                    found     = True
                    atomLabel = newLabel
                newLabels.append (atomLabel)
            if found:
                newGroup = AminoGroup (natoms=group.natoms, centralAtom=group.centralAtom, radius=group.radius, labels=newLabels, symbol=group.symbol)
                group    = newGroup
            newGroups.append (group)
        self.groups = newGroups


    # . Convert atom types Enzymix -> CHARMM
    _DEFAULT_CONVERT_TYPE = {
        "P4"    :   "P2"    ,
        "O3"    :   "ON3"   ,
        "O4"    :   "ON2"   ,
        "H4"    :   "HN8"   ,
        "CT"    :   "CN8"   ,
        }
    def WriteToCHARMM (self, filename=None, convertTypes=_DEFAULT_CONVERT_TYPE):
        """Convert to CHARMM format."""
        output = []
        # . Write header
        output.append ("RESI %s    %.2f%s" % (self.name, self.charge, ("  ! %s" % self.title) if self.title else ""))
        # . Write groups of atoms
        for group in self.groups:
            output.append ("GROUP")
            groupCharge = 0.
            for iatom, atomLabel in enumerate (group.labels, 1):
                for atom in self.atoms:
                    if atom.atomLabel == atomLabel:
                        groupCharge += atom.atomCharge
                        atomType = atom.atomType
                        if convertTypes:
                            if convertTypes.has_key (atom.atomType):
                                atomType = convertTypes[atom.atomType]
                        groupSummary = ""
                        if iatom == len (group.labels):
                            groupSummary = "  ! Charge: %5.2f" % groupCharge
                        output.append ("ATOM %-4s %-4s    %5.2f%s" % (atom.atomLabel, atomType, atom.atomCharge, groupSummary))
                        break
            output.append ("!")
        # . Write bonds
        counter = 0
        line    = "BOND "
        for (bonda, bondb) in self.bonds:
            line = "%s %-4s %-4s    " % (line, bonda, bondb)
            counter += 1
            if counter > 4:
                output.append (line)
                counter = 0
                line    = "BOND "
        if line:
            output.append (line)
        output.append ("!")
        # . Write to a file or terminal
        if filename:
            fo = open (filename, "w")
            for line in output:
                fo.write ("%s\n" % line)
            fo.close ()
        else:
            for line in output:
                print line


    def GenerateAngles (self, quiet=False):
        """Automatically generate a list of angles."""
        angles = []
        # . Outer loop
        for i, (bonda, bondb) in enumerate (self.bonds):
            # . Inner loop
            for j, (othera, otherb) in enumerate (self.bonds):
                if i != j:
                    angle = None
                    #   (a, b)
                    #      (c, d)
                    if   bondb == othera:
                        angle = (bonda, bondb, otherb)
                    #      (a, b)
                    #   (c, d)
                    elif bonda == otherb:
                        angle = (othera, bonda, bondb)
                    #   (a, b)
                    #      (d, c)
                    elif bondb == otherb:
                        angle = (bonda, bondb, othera)
                    #      (a, b)
                    #   (d, c)
                    elif bonda == othera:
                        angle = (otherb, bonda, bondb)
                    if angle:
                        (a, b, c) = angle
                        elgna = (c, b, a)
                        if (angle not in angles) and (elgna not in angles):
                            angles.append (angle)
        self.angles = angles
        if not quiet:
            print ("# . Generated %d angles" % self.nangles)


    def GenerateTorsions (self, quiet=False):
        """Automatically generate a list of torsions (=dihedral angles)."""
        if hasattr (self, "angles"):
            torsions = []
            # . Outer loop
            for i, (anglea, angleb, anglec) in enumerate (self.angles):
                # . Inner loop
                for j, (othera, otherb, otherc) in enumerate (self.angles):
                    if i != j:
                        torsion = None
                        #   (a, b, c)
                        #      (d, e, f)
                        if   (angleb == othera) and (anglec == otherb):
                            torsion = (anglea, angleb, anglec, otherc)
                        #      (a, b, c)
                        #   (d, e, f)
                        elif (anglea == otherb) and (angleb == otherc):
                            torsion = (othera, anglea, angleb, anglec)
                        #   (a, b, c)
                        #      (f, e, d)
                        elif (angleb == otherc) and (anglec == otherb):
                            torsion = (anglea, angleb, anglec, othera)
                        #      (a, b, c)
                        #   (f, e, d)
                        elif (anglea == otherb) and (angleb == otherc):
                            torsion = (otherc, anglea, angleb, anglec)
                        if torsion:
                            (a, b, c, d) = torsion
                            noisrot = (d, c, b, a)
                            if (torsion not in torsions) and (noisrot not in torsions):
                                torsions.append (torsion)
            self.torsions = torsions
        if not quiet:
            print ("# . Generated %d torsions" % self.ntorsions)


    def _BondsToTypes (self):
        types  = []
        for (bonda, bondb) in self.bonds:
            for atom in self.atoms:
                if   atom.atomLabel == bonda:
                    typea = atom.atomType
                elif atom.atomLabel == bondb:
                    typeb = atom.atomType
            pair = (typea, typeb)
            types.append (pair)
        unique = []
        for (typea, typeb) in types:
            if (typea, typeb) not in unique:
                if (typeb, typea) not in unique:
                    pair = (typea, typeb)
                    unique.append (pair)
        return (types, unique)


    def _AnglesToTypes (self):
        types  = []
        for (anglea, angleb, anglec) in self.angles:
            for atom in self.atoms:
                if   atom.atomLabel == anglea:
                    typea = atom.atomType
                elif atom.atomLabel == angleb:
                    typeb = atom.atomType
                elif atom.atomLabel == anglec:
                    typec = atom.atomType
            triplet = (typea, typeb, typec)
            types.append (triplet)
        unique = []
        for (typea, typeb, typec) in types:
            if (typea, typeb, typec) not in unique:
                if (typec, typeb, typea) not in unique:
                    triplet = (typea, typeb, typec)
                    unique.append (triplet)
        return (types, unique)


    def _TorsionsToTypes (self):
        types   = []
        for (torsiona, torsionb, torsionc, torsiond) in self.torsions:
            for atom in self.atoms:
                if   atom.atomLabel == torsiona:
                    typea = atom.atomType
                elif atom.atomLabel == torsionb:
                    typeb = atom.atomType
                elif atom.atomLabel == torsionc:
                    typec = atom.atomType
                elif atom.atomLabel == torsiond:
                    typed = atom.atomType
            quadruplet = (typea, typeb, typec, typed)
            types.append (quadruplet)
        unique  = []
        for (typea, typeb, typec, typed) in types:
            if (typea, typeb, typec, typed) not in unique:
                if (typed, typec, typeb, typea) not in unique:
                    quadruplet = (typea, typeb, typec, typed)
                    unique.append (quadruplet)
        general = []
        for (typea, typeb, typec, typed) in types:
            if (typeb, typec) not in general:
                if (typec, typeb) not in general:
                    pair = (typeb, typec)
                    general.append (pair)
        return (types, unique, general)


    def WriteTopology (self, writeTypes=False, filename=""):
        """Write object's bonds, angles and dihedrals."""
        lines = ["*** Bonds ***", ]
        bondTypes, bondUnique = self._BondsToTypes ()
        for i, ((bonda, bondb), (typea, typeb)) in enumerate (zip (self.bonds, bondTypes), 1):
            types = ""
            if writeTypes:
                types = " " * 10 + "# %-4s    %-4s" % (typea, typeb)
            lines.append ("%3d    %-4s    %-4s%s" % (i, bonda, bondb, types))
        
        if hasattr (self, "angles"):
            lines.append ("*** Angles ***")
            angleTypes, angleUnique = self._AnglesToTypes ()
            for i, ((anglea, angleb, anglec), (typea, typeb, typec)) in enumerate (zip (self.angles, angleTypes), 1):
                types = ""
                if writeTypes:
                    types = " " * 10 + "# %-4s    %-4s    %-4s" % (typea, typeb, typec)
                lines.append ("%3d    %-4s    %-4s    %-4s%s" % (i, anglea, angleb, anglec, types))

        if hasattr (self, "torsions"):
            lines.append ("*** Torsions ***")
            torsionTypes, torsionUnique, torsionGeneral = self._TorsionsToTypes ()
            for i, ((torsiona, torsionb, torsionc, torsiond), (typea, typeb, typec, typed)) in enumerate (zip (self.torsions, torsionTypes), 1):
                types = ""
                if writeTypes:
                    types = " " * 10 + "# %-4s    %-4s    %-4s    %-4s" % (typea, typeb, typec, typed)
                lines.append ("%3d    %-4s    %-4s    %-4s    %-4s%s" % (i, torsiona, torsionb, torsionc, torsiond, types))

            lines.append ("*** General torsions ***")
            general      = []
            generalTypes = []
            for (torsiona, torsionb, torsionc, torsiond), (typea, typeb, typec, typed) in zip (self.torsions, torsionTypes):
                pair = (torsionb, torsionc)
                reverse = (torsionc, torsionb)
                if (pair not in general) and (reverse not in general):
                    general.append (pair)
                    types = (typeb, typec)
                    generalTypes.append (types)
            for i, ((torsionb, torsionc), (typeb, typec)) in enumerate (zip (general, generalTypes), 1):
                types = ""
                if writeTypes:
                    types = " " * 10 + "# %-4s    %-4s    %-4s    %-4s" % ("@@", typeb, typec, "@@")
                lines.append ("%3d    %-4s    %-4s    %-4s    %-4s%s" % (i, "@@", torsionb, torsionc, "@@", types))

        if not filename:
            for line in lines:
                print line
        else:
            fo = open (filename, "w")
            for line in lines:
                fo.write (line + "\n")
            fo.close ()


    def WriteTypes (self, filename="", parameters=None):
        """Write object's types for bonds, angles and dihedrals."""
        includeParameters = isinstance (parameters, ParametersLibrary)

        lines = ["*** Bond types ***", ]
        bondTypes, bondUnique = self._BondsToTypes ()
        for i, (typea, typeb) in enumerate (bondUnique, 1):
            par = ""
            if includeParameters:
                bond = parameters.GetBond (typea, typeb)
                if bond:
                    par = "    %6.1f    %6.2f" % (bond.k, bond.r0)
            lines.append ("%3d    %-4s    %-4s%s" % (i, typea, typeb, par))

        if hasattr (self, "angles"):
            lines.append ("*** Angle types ***")
            angleTypes, angleUnique = self._AnglesToTypes ()
            for i, (typea, typeb, typec) in enumerate (angleUnique, 1):
                par = ""
                if includeParameters:
                    angle = parameters.GetAngle (typea, typeb, typec)
                    if angle:
                        par = "    %6.1f    %6.2f" % (angle.k, angle.r0)
                lines.append ("%3d    %-4s    %-4s    %-4s%s" % (i, typea, typeb, typec, par))

        if hasattr (self, "torsions"):
            lines.append ("*** Torsion types ***")
            torsionTypes, torsionUnique, torsionGeneral = self._TorsionsToTypes ()
            for i, (typea, typeb, typec, typed) in enumerate (torsionUnique, 1):
                par = ""
                if includeParameters:
                    torsion = parameters.GetTorsion (typeb, typec)
                    if torsion:
                        par = "    %1d    %6.2f    %6.1f" % (torsion.periodicity, torsion.k, torsion.phase)
                lines.append ("%3d    %-4s    %-4s    %-4s    %-4s%s" % (i, typea, typeb, typec, typed, par))

            lines.append ("*** General torsion types ***")
            for i, (typeb, typec) in enumerate (torsionGeneral, 1):
                par = ""
                if includeParameters:
                    torsion = parameters.GetTorsion (typeb, typec)
                    if torsion:
                        par = "    %1d    %6.2f    %6.1f" % (torsion.periodicity, torsion.k, torsion.phase)
                lines.append ("%3d    %-4s    %-4s    %-4s    %-4s%s" % (i, "@@", typeb, typec, "@@", par))

        lines.append ("*** Van der Waals and mass types ***")
        atomUnique = []
        for atom in self.atoms:
            if atom.atomType not in atomUnique:
                atomUnique.append (atom.atomType)
        for i, atomType in enumerate (atomUnique, 1):
            par = ""
            if includeParameters:
                vdw = parameters.GetVDW (atomType)
                if vdw:
                    par = "    %8.1f    %8.1f    %6.2f" % (vdw.repulsive, vdw.attractive, vdw.mass)
            lines.append ("%3d    %-4s%s" % (i, atomType, par))

        if not filename:
            for line in lines:
                print line
        else:
            fo = open (filename, "w")
            for line in lines:
                fo.write (line + "\n")
            fo.close ()


#===============================================================================
_DEFAULT_LIBRARY_FILE   = os.path.join (os.environ["HOME"], "DNA_polymerase", "libs", "amino98_custom_small.lib")


class AminoLibrary (object):
    """A class to represent data from the Molaris amino98.lib file."""

    def __init__ (self, filename=_DEFAULT_LIBRARY_FILE, logging=True, reorder=True, unique=False, verbose=False):
        """Constructor."""
        self.filename = filename
        self._Parse (logging=logging, reorder=reorder, unique=unique, verbose=verbose)
        self._i = 0


    def __len__ (self):
        return self.ncomponents


    # . The next 3 methods are for the iterator
    def __iter__ (self):
        return self

    def __next__ (self):
        return self.next ()

    def next (self):
        """Next component."""
        if self._i >= self.ncomponents:
            self._i = 0
            raise exceptions.StopIteration ()
        else:
            self._i += 1
        return self.components[self._i - 1]


    def _FindComponent (self, key):
        if isinstance (key, int):
            # . Search by serial
            for component in self.components:
                if component.serial == key:
                    return component
        elif isinstance (key, str):
            # . Search by name
            for component in self.components:
                if component.name == key:
                    return component
        else:
            raise exceptions.StandardError ("Unknown type of key.")
        # . Component not found
        return None


    def has_key (self, key):
        """Checks for a component in the library."""
        return self.__contains__ (key)


    def __contains__ (self, key):
        """Checks for a component in the library."""
        component = self._FindComponent (key)
        if component:
            return True
        return False


    def __getitem__ (self, key):
        """Find and return a component from the library."""
        component = self._FindComponent (key)
        if not component:
            raise exceptions.StandardError ("Component %s not found in the library." % key)
        return component


    @property
    def ncomponents (self):
        if hasattr (self, "components"):
            return len (self.components)
        else:
            return 0


    @property
    def lastSerial (self):
        serial = 1
        if self.ncomponents > 1:
            for component in self.components:
                serial = component.serial
        return serial


    def _GetCleanLine (self, data):
        line      = data.next ()
        lineClean = line[:line.find ("!")].strip ()
        return lineClean


    def _GetLineWithComment (self, data):
        line      = data.next ()
        position  = line.find ("!")
        if position > -1:
            text      = line[             : position].strip ()
            comment   = line[position + 1 :         ].strip ()
        else:
            text      = line
            comment   = ""
        return (text, comment)


    def _Parse (self, logging, reorder, unique, verbose=False):
        components = []
        names      = []
        data       = open (self.filename)
        try:
            while True:
                line = self._GetCleanLine (data)
                # . Check if a new residue starts
                if line.startswith ("---"):
                    # . Get serial and name
                    line, title  = self._GetLineWithComment (data)
                    entry = TokenizeLine (line, converters=[None, ])[0]
                    # . Remove spaces
                    entry = entry.replace (" ", "")
                    # . Check if last residue found
                    if entry == "0":
                        break
                    for i, char in enumerate (entry):
                        if not char.isdigit ():
                            break
                    componentSerial, name = int (entry[:i]), entry[i:]
                    # . Check if the component label is unique
                    if unique:
                        if name in names:
                            raise exceptions.StandardError ("Component label %s is not unique." % name)
                        names.append (name)
                    # . Get number of atoms
                    line    = self._GetCleanLine (data)
                    natoms  = int (line)
                    # . Initiate conversion table serial->label
                    convert = {}
                    # . Read atoms
                    atoms   = []
                    labels  = []
                    for i in range (natoms):
                        line = self._GetCleanLine (data)
                        atomNumber, atomLabel, atomType, atomCharge = TokenizeLine (line, converters=[int, None, None, float])
                        if unique:
                            # . Check if the atom label is unique
                            if atomLabel in labels:
                                raise exceptions.StandardError ("Component %s %d: Atom label %s is not unique." % (name, serial, atomLabel))
                            labels.append (atomLabel)
                        # . Create atom
                        atom = AminoAtom (atomLabel=atomLabel, atomType=atomType, atomCharge=atomCharge)
                        atoms.append (atom)
                        # . Update conversion table serial->label
                        convert[atomNumber] = atomLabel
                    # . Get number of bonds
                    line   = self._GetCleanLine (data)
                    nbonds = int (line)
                    # . Read bonds
                    bonds  = []
                    for i in range (nbonds):
                        line = self._GetCleanLine (data)
                        atoma, atomb = TokenizeLine (line, converters=[int, int])
                        if reorder:
                            # . Keep the lower number first
                            if atoma > atomb:
                                atoma, atomb = atomb, atoma
                        bonds.append ((atoma, atomb))
                    if reorder:
                        # . Sort bonds
                        bonds.sort (key=lambda bond: bond[0])
                    # . Convert numerical bonds to labeled bonds
                    labeledBonds = []
                    for atoma, atomb in bonds:
                        # . FIXME: Workaround for invalid entries in the amino file
                        try:
                            pair = (convert[atoma], convert[atomb])
                            labeledBonds.append (pair)
                        except:
                            pass
                    bonds = labeledBonds
                    # . Read connecting atoms
                    line  = self._GetCleanLine (data)
                    seriala, serialb = TokenizeLine (line, converters=[int, int])
                    # . Convert serials of connecting atoms to labels
                    connecta, connectb = "", ""
                    if seriala > 0:
                        connecta = convert[seriala]
                    if serialb > 0:
                        connectb = convert[serialb]
                    # . Read number of electroneutral groups
                    line    = self._GetCleanLine (data)
                    ngroups = int (line)
                    # . Read groups
                    groups  = []
                    for i in range (ngroups):
                        line     = self._GetCleanLine (data)
                        nat, central, radius = TokenizeLine (line, converters=[int, int, float])
                        line     = self._GetCleanLine (data)
                        serials  = TokenizeLine (line, converters=[int] * nat)
                        # . Convert central atom's serial to a label
                        # . FIXME: Workaround for invalid entries in the amino file
                        try:
                            central  = convert[central]
                            # . Convert serials to labels
                            labels   = []
                            for serial in serials:
                                labels.append (convert[serial])
                            symbol   = chr (ord (_GROUP_START) + i)
                            group    = AminoGroup (natoms=nat, centralAtom=central, radius=radius, labels=labels, symbol=symbol)
                            groups.append (group)
                        except:
                            pass
                    # . Create a component and add it to the list
                    component = AminoComponent (serial=componentSerial, name=name, atoms=atoms, bonds=bonds, groups=groups, connect=(connecta, connectb), logging=logging, title=title, verbose=verbose)
                    components.append (component)
        except StopIteration:
            pass
        # . Finish up
        data.close ()
        if logging:
            ncomponents = len (components)
            print ("Found %d component%s." % (ncomponents, "s" if ncomponents > 1 else ""))
        self.components = components


    def WriteAll (self, showGroups=False, showLabels=False):
        """Write out all components from the library."""
        for component in self.components[:-1]:
            component.Write (showGroups=showGroups, showLabels=showLabels, terminate=False)

        # . Write the last component
        component = self.components[-1]
        component.Write (showGroups=showGroups, showLabels=showLabels, terminate=True)


#===============================================================================
# . Main program
#===============================================================================
if __name__ == "__main__": pass
