let parse_args () =
  if Array.length Sys.argv < 2 then None
  else int_of_string_opt Sys.argv.(1)


let beep () =
  if Sys.file_exists "/usr/bin/pw-play" then
    ignore (Sys.command "pw-play /usr/share/sounds/freedesktop/stereo/complete.oga")
  else
    ignore (Sys.command "afplay /System/Library/Sounds/Glass.aiff")

let () =
  match parse_args () with
  | None ->
    print_endline "Usage: utility-timer <seconds : integer>";
    exit 1
  | Some seconds ->
    for i = seconds downto 1 do
      Printf.printf "\r%-10d%!" i;
      Unix.sleepf 1.0
    done;

    Printf.printf "\rDONE!\n%!";
    beep ()
