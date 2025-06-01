"use client";

import { useState } from "react";
import { AdminPageTitle } from "@/components/admin/Title";
import { DatabaseIcon, InfoIcon } from "@/components/icons/icons";
import Text from "@/components/ui/text";
import { Separator } from "@/components/ui/separator";
import Link from "next/link";
import CreateButton from "@/components/ui/createButton";
import { usePopup } from "@/components/admin/connectors/Popup";
import { ThreeDotsLoader } from "@/components/Loading";
import CardSection from "@/components/admin/CardSection";
import { useDatasets } from "./hooks";
import { Dataset } from "./lib";
import { formatDistanceToNow, format } from "date-fns";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { FiLock, FiUnlock, FiEdit2, FiExternalLink, FiDatabase } from "react-icons/fi";
import { useRouter } from "next/navigation";
import { PageSelector } from "@/components/PageSelector";
import { getSourceMetadata } from "@/lib/sources";

const numToDisplay = 10;

interface DatasetTableProps {
  datasets: Dataset[];
}

const DataSourceDisplay = ({ ccPairDescriptor }: { ccPairDescriptor: any }) => {
  const sourceMetadata = getSourceMetadata(ccPairDescriptor.connector.source);
  
  return (
    <div className="flex items-center text-blue-500 dark:text-blue-100">
      {sourceMetadata.icon({ size: 16 })}
      <div className="ml-1 my-auto text-xs font-medium truncate">
        {ccPairDescriptor.name || sourceMetadata.displayName}
      </div>
    </div>
  );
};

const DatasetTable = ({ datasets }: DatasetTableProps) => {
  const [page, setPage] = useState(1);
  const router = useRouter();

  // Sort datasets by creation date (newest first)
  const sortedDatasets = [...datasets].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div>
      <Table className="overflow-visible mt-2">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Data Sources</TableHead>
            <TableHead>Access</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedDatasets
            .slice((page - 1) * numToDisplay, page * numToDisplay)
            .map((dataset) => (
              <TableRow key={dataset.id}>
                <TableCell className="whitespace-normal break-all">
                  <div className="flex items-center gap-x-1 text-emphasis">
                    <span className="font-medium">{dataset.name}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="max-w-md truncate">
                    {dataset.description || "No description provided"}
                  </div>
                </TableCell>
                <TableCell>
                  <div>
                    {dataset.cc_pair_descriptors.map((ccPairDescriptor, ind) => (
                      <div
                        className={ind !== dataset.cc_pair_descriptors.length - 1 ? "mb-3" : ""}
                        key={ccPairDescriptor.id}
                      >
                        <DataSourceDisplay ccPairDescriptor={ccPairDescriptor} />
                      </div>
                    ))}
                    {dataset.cc_pair_descriptors.length === 0 && (
                      <span className="text-text-muted text-sm">No data sources</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {dataset.is_public ? (
                    <Badge variant="success" icon={FiUnlock}>
                      Public
                    </Badge>
                  ) : (
                    <Badge variant="private" icon={FiLock}>
                      Private
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="text-sm text-text-muted">
                    {format(new Date(dataset.created_at), "MMM d, yyyy")}
                  </div>
                </TableCell>
              </TableRow>
            ))}
        </TableBody>
      </Table>

      {datasets.length > numToDisplay && (
        <div className="mt-3 flex">
          <div className="mx-auto">
            <PageSelector
              totalPages={Math.ceil(datasets.length / numToDisplay)}
              currentPage={page}
              onPageChange={(newPage) => setPage(newPage)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

const Main = () => {
  const { popup, setPopup } = usePopup();
  const { data: datasets, isLoading, error } = useDatasets();

  return (
    <div className="mb-8">
      {popup}
      <Text className="mb-3">
        <b>Datasets</b> allow you to organize and manage datasets for analysis with the code interpreter.
        You can add data sources to create datasets which can be used for analysis without being indexed for search.
      </Text>

      <div className="mb-3"></div>

      <div className="flex mb-6">
        <CreateButton
          href="/admin/documents/datasets/new"
          text="New Dataset"
        />
        <Link 
          href="/admin/documents/datasets/settings" 
          className="ml-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-md flex items-center text-sm"
        >
          <FiDatabase className="mr-2" /> Dataset Settings
        </Link>
      </div>

      <Separator />
      
      <div className="mt-6">
        {isLoading ? (
          <div className="text-center">
            <ThreeDotsLoader />
          </div>
        ) : error ? (
          <div className="text-center text-red-500">
            <p>Error loading datasets: {error}</p>
          </div>
        ) : datasets && datasets.length > 0 ? (
          <DatasetTable datasets={datasets} />
        ) : (
          <div className="text-center text-text-muted">
            <p>No datasets created yet. Create a dataset to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const Page = () => {
  return (
    <div className="container mx-auto">
      <AdminPageTitle icon={<DatabaseIcon size={32} />} title="Datasets" />

      <Main />
    </div>
  );
};

export default Page; 