type duration = Seconds of int | Minutes of int

let parse_args () =
  let argv = Sys.argv in
  let argc = Array.length argv in
  if argc < 3 then None
  else
    match (argv.(1), int_of_string_opt argv.(2)) with
    | "-s", Some n -> Some (Seconds n)
    | "-m", Some n -> Some (Minutes n)
    | _ -> None

let format_time seconds =
  Printf.sprintf "%d:%02d" (seconds / 60) (seconds mod 60)

let beep () =
  if Sys.file_exists "/usr/bin/pw-play" then
    ignore
      (Sys.command "pw-play /usr/share/sounds/freedesktop/stereo/complete.oga")
  else ignore (Sys.command "afplay /System/Library/Sounds/Glass.aiff")

let () =
  match parse_args () with
  | None ->
      Printf.eprintf "Usage: %s -s <seconds> OR -m <minutes>\n" Sys.argv.(0);
      exit 1
  | Some (Seconds n | Minutes n) when n <= 0 ->
      prerr_endline "Timer duration must be greater than 0!\n";
      exit 1
  | Some duration ->
      let seconds =
        match duration with Seconds n -> n | Minutes n -> n * 60
      in

      for i = seconds downto 1 do
        Printf.printf "\r%-10s%!" (format_time i);
        Unix.sleepf 1.0
      done;

      Printf.printf "\rDONE!\n%!";
      beep ()
