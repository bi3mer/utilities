let usage = "Usage: {name} [options]"

let () =
  Arg.parse [] (fun _ -> ()) usage;
  print_endline "TODO: implement"
