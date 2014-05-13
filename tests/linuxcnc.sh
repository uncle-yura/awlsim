# LinuxCNC hardware module test

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"
	export PYTHONPATH="$rootdir/linuxcnc_fake_hal"
	"$interpreter" ./awlsim-linuxcnc-hal --check-cnc 0 --onecycle EXAMPLE.awl
}
