# Use the maintainer's immutable 2.12 release commit when the release-archive
# host is unavailable. Git object identity replaces the inactive tarball URL;
# the original recipe's license checks and local C23 fix remain unchanged.
SRC_URI:remove = "http://dotat.at/prog/${BPN}/${BP}.tar.xz"
SRC_URI:append = " git://github.com/fanf2/unifdef.git;protocol=https;nobranch=1"
SRCREV = "99d17074b9ba66cc9da2ce60fb29c6b1beb0370a"
S = "${WORKDIR}/${BP}"

# The release archive normally contains generated version files. Generate them
# from the annotated upstream tag before Yocto applies its existing patch. Keep
# the Git fetch checkout separately, and build the same source files without
# .git, as the original release archive does, so the version remains stable.
do_unpack[postfuncs] += "unifdef_release_version"
python unifdef_release_version() {
    import subprocess
    import shutil
    from pathlib import Path
    source = Path(d.getVar('WORKDIR'), 'git')
    target = Path(d.getVar('S'))
    tag = subprocess.check_output(
        ['git', 'describe', '--exact-match', d.getVar('SRCREV')],
        cwd=source, text=True).strip()
    if tag != 'unifdef-2.12':
        bb.fatal('Expected annotated upstream unifdef-2.12 tag, got ' + tag)
    subprocess.run(['sh', 'scripts/reversion.sh'], cwd=source, check=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git'))
}
