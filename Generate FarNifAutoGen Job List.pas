{

}
unit GenerateFarNifAutoGenJobList;

var
	bDeleteSkipped, bSkipInjection, bRefExactCoords, bRefExactBaseObj, bRefExactBaseClass, bRefMatchLastPass, doOnce: boolean;
	masterFile: IInterface;
	morrowindMasterIndex: integer;
	numDeletedRecords, numRecordsSkipped, numRecordsInTargetFile, numRecordsRenumbered, numTotalRecordsRead, numCellsRead, numMastersFound: integer;
	targetFile: IInterface;
	stringbuffer: TStringList;


//===========================================================================
////////////////////////////////////////////////////////////////////////////
// INITIALIZE
////////////////////////////////////////////////////////////////////////////
//===========================================================================
function Initialize: integer;
begin

	stringbuffer:= TStringList.Create;
	stringbuffer.Sorted := True;

	if not wbSimpleRecords then begin
		MessageDlg('Simple records must be checked in xEdit options', mtInformation, [mbOk], 0);
		Result := 1;
		Exit;
	end;
  
  
//	if not OptionsForm then begin
//		Result := 1;
//		Exit;
//	end;

	targetFile := nil;
	numDeletedRecords := 0;
	numRecordsRenumbered := 0;
	numCellsRead := 0;
	numMastersFound := 0;
	numTotalRecordsRead := 0;
	numRecordsSkipped := 0;
	numRecordsInTargetFile := 0;
	doOnce := false;
end;


//===========================================================================
// Synchronize PlacedObject References with Master
//===========================================================================
function SynchronizePlacedObject(e: IInterface): integer;
var
	refScale: double;
	modelName, refScaleString, recordInfo: string;
	masterReference, originalRecord, targetWorld, masterWorld, masterCell, targetCell: IInterface;
	targetOffset, masterOffset: cardinal;
	newlocalID, loadorderMasterID, loadorderTargetID: cardinal;
	baseRecordSignature, baseRecordEditorID, worldName, targetEditorID: string;
	indexVal, GridX, GridY, offset, i, threshold, data_flags: integer;
	lrX, lrY, lrZ, lX, lY, lZ: double;
//	targetPos: TwbVector;
begin

	// Draft Pseudocode:
	// 1. get XYZ data, get base record EditorID
	// 2. get local parent CELL and match to master parent CELL
	// 3. get children of master parent CELL
	// 4. foreach master child, compare XYZ to e.  If within threshold then...
	// 5.		if toggleEditorIDMatch: check for editorID match, if not then skip
	// 6.		else inject into master
	// 7.TODO:			if toggleOverridePositionOnly, copy master to new record then overwrite with local XYZ
	// 8.			else if toggleOverrideAll, inject local record into master ID

	loadorderTargetID := GetLoadOrderFormID(e);
	targetEditorID := EditorID(e);

	originalRecord := BaseRecord(e);
	baseRecordEditorID := EditorID(originalRecord);
	baseRecordSignature := Signature(originalRecord);

	// call function to search for a bestmatch to target record. 
	// syntax for function is FindRefByBestMatch(masterCell, targetRecord, CoordinateThreshold, bMustMatchBaseEditorID, bMustMatchBaseSignature)

	if (baseRecordSignature = 'STAT') then begin
		modelName := GetElementNativeValues(originalRecord, 'Model\MODL');
//		refScale := GetElementNativeValues(e, 'XSCL');
		refScaleString := GetElementEditValues(e, 'XSCL');
		if (refScaleString = '') then begin
			refScaleString := '1.000';
		end;
		modelName := LowerCase(modelName);
		refScaleString := Copy(refScaleString, 1, 4);
		recordInfo := Format('meshes/%s,%s', [modelName, refScaleString]);
		if (stringbuffer.Find(recordInfo,indexVal) = False) then begin
			stringbuffer.Add(recordInfo);
//			AddMessage( Format('STAT: [%s] = %s', [baseRecordEditorID, recordInfo]) );
		end;
	end
	else begin
		inc(numRecordsSkipped);
	end;


end;


//===========================================================================
function Process(e: IInterface): integer;
var
	cell, group: IInterface;
//	isinterior: boolean;
	percentComplete: single;
	data_flags: integer;
begin


	if (targetFile <> GetFile(e)) then begin
		targetFile := GetFile(e);
		numRecordsInTargetFile := numRecordsInTargetFile + RecordCount(targetFile);
	end;
	
	// If cell exterior type, then prepare perform XY link
	// If not exterior cell type, then perform standard record Synch

	if (Signature(e) = 'REFR') then begin
//		addmessage( 'DEBUG: REFR');
		SynchronizePlacedObject(e);
	end;

	// Do statistics tracking and update messages

	Inc(numTotalRecordsRead);

	if (numTotalRecordsRead mod 100000 = 0) and (numTotalRecordsRead > 0) then begin
		if (numRecordsInTargetFile = 0) then
			numRecordsInTargetFile := RecordCount(targetFile);
		percentComplete := (numTotalRecordsRead / numRecordsInTargetFile) * 100;
		AddMessage( Format('%4f percent of records in target file read (%d of %d total records). %d records skipped.', [percentComplete, numTotalRecordsRead, numRecordsInTargetFile, numRecordsSkipped]) );
	end;

end;

//===========================================================================
function Finalize: integer;
var
  fname: string;
begin
	AddMessage( Format('Script Completed. Total stats: %d records read, %d records skipped.', [numTotalRecordsRead, numRecordsSkipped]) );
	fname := ProgramPath + 'nif_list.job';
	AddMessage('Saving list to ' + fname);
	stringbuffer.SaveToFile(fname);
	stringbuffer.Free;

end;

end.
